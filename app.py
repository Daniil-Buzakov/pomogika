import os
import uuid
from datetime import datetime, timedelta
from flask import (Flask, render_template, redirect, url_for, flash, request,
                   abort, jsonify)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from models import db, User, Ad, AdPhoto, Chat, Message, Review
from forms import RegisterForm, LoginForm, AdForm, ReviewForm, ProfileForm

# ---------- Конфигурация ----------
load_dotenv()

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-only-fallback")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pomogika.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)
if os.environ.get("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True

# ---------- Cloudinary ----------
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Войдите, чтобы продолжить"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_unread():
    if current_user.is_authenticated:
        chats = Chat.query.filter(
            (Chat.user1_id == current_user.id) | (Chat.user2_id == current_user.id)
        ).all()
        total = sum(c.unread_for(current_user.id) for c in chats)
        return {"unread_count": total}
    return {"unread_count": 0}


# ---------- Утилиты ----------
def upload_to_cloudinary(file, folder="pomogika"):
    """Загружает файл в Cloudinary и возвращает URL или None."""
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return None
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image",
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None


def cleanup_old_messages():
    cutoff = datetime.utcnow() - timedelta(days=30)
    deleted = Message.query.filter(Message.created_at < cutoff).delete()
    if deleted:
        db.session.commit()


# ---------- Главная ----------
@app.route("/")
def index():
    cleanup_old_messages()
    q = request.args.get("q", "").strip()
    city = request.args.get("city", "").strip()
    ad_type = request.args.get("type", "").strip()
    category = request.args.get("category", "").strip()

    query = Ad.query.filter_by(status="active")
    if q:
        query = query.filter(Ad.title.contains(q))
    if city:
        query = query.filter(Ad.city.contains(city))
    if ad_type in ("pomosch", "podrabotka"):
        query = query.filter(Ad.type == ad_type)
    if category:
        query = query.filter(Ad.category == category)

    ads = query.order_by(Ad.created_at.desc()).all()
    return render_template("index.html", ads=ads)


@app.route("/my-ads")
@login_required
def my_ads():
    ads = Ad.query.filter_by(author_id=current_user.id)\
        .order_by(Ad.created_at.desc()).all()
    return render_template("my_ads.html", ads=ads)


# ---------- Авторизация ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Такой email уже занят", "danger")
        else:
            user = User(
                name=form.name.data,
                email=form.email.data,
                password=generate_password_hash(form.password.data),
                phone=form.phone.data or None,
                city=form.city.data or None,
                is_business=form.is_business.data,
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Добро пожаловать на Помогику!", "success")
            return redirect(url_for("index"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Вы вошли", "success")
            return redirect(request.args.get("next") or url_for("index"))
        flash("Неверный email или пароль", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли", "info")
    return redirect(url_for("index"))


# ---------- Объявления ----------
@app.route("/ads/new", methods=["GET", "POST"])
@login_required
def new_ad():
    form = AdForm()
    if form.validate_on_submit():
        price_unit = "hour" if form.type.data == "podrabotka" else "task"
        ad = Ad(
            title=form.title.data,
            description=form.description.data,
            type=form.type.data,
            category=form.category.data,
            price=form.price.data,
            price_unit=price_unit,
            city=form.city.data,
            address=form.address.data or None,
            author_id=current_user.id,
        )
        db.session.add(ad)
        db.session.flush()

        for f in request.files.getlist("photos"):
            url = upload_to_cloudinary(f, folder="pomogika/ads")
            if url:
                db.session.add(AdPhoto(url=url, ad_id=ad.id))

        db.session.commit()
        flash("Объявление опубликовано", "success")
        return redirect(url_for("ad_detail", ad_id=ad.id))
    return render_template("new_ad.html", form=form)


@app.route("/ads/<int:ad_id>")
def ad_detail(ad_id):
    ad = db.session.get(Ad, ad_id) or abort(404)
    return render_template("ad.html", ad=ad)


@app.route("/ads/<int:ad_id>/close", methods=["POST"])
@login_required
def close_ad(ad_id):
    ad = db.session.get(Ad, ad_id) or abort(404)
    if ad.author_id != current_user.id:
        abort(403)
    ad.status = "done"
    db.session.commit()
    flash("Объявление завершено", "info")
    return redirect(url_for("ad_detail", ad_id=ad.id))


# ---------- Чат ----------
def get_or_create_chat(ad, user):
    if user.id == ad.author_id:
        return None
    chat = Chat.query.filter_by(ad_id=ad.id, user2_id=user.id).first()
    if not chat:
        chat = Chat(ad_id=ad.id, user1_id=ad.author_id, user2_id=user.id)
        db.session.add(chat)
        db.session.commit()
    return chat


@app.route("/ads/<int:ad_id>/write", methods=["POST"])
@login_required
def write_to_ad(ad_id):
    ad = db.session.get(Ad, ad_id) or abort(404)
    if ad.author_id == current_user.id:
        flash("Это ваше объявление", "warning")
        return redirect(url_for("ad_detail", ad_id=ad.id))
    chat = get_or_create_chat(ad, current_user)
    return redirect(url_for("chat_view", chat_id=chat.id))


@app.route("/chats")
@login_required
def chats_list():
    cleanup_old_messages()
    chats = Chat.query.filter(
        (Chat.user1_id == current_user.id) | (Chat.user2_id == current_user.id)
    ).order_by(Chat.created_at.desc()).all()
    return render_template("chats.html", chats=chats)


@app.route("/chats/<int:chat_id>", methods=["GET", "POST"])
@login_required
def chat_view(chat_id):
    chat = db.session.get(Chat, chat_id) or abort(404)
    if current_user.id not in (chat.user1_id, chat.user2_id):
        abort(403)

    cleanup_old_messages()

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text:
            db.session.add(Message(chat_id=chat.id,
                                   sender_id=current_user.id,
                                   text=text))
            db.session.commit()
        return redirect(url_for("chat_view", chat_id=chat.id))

    changed = False
    for m in chat.messages:
        if m.sender_id != current_user.id and not m.is_read:
            m.is_read = True
            changed = True
    if changed:
        db.session.commit()

    other = chat.other_user(current_user.id)
    return render_template("chat.html", chat=chat, other=other)


@app.route("/api/chat/<int:chat_id>/messages")
@login_required
def api_chat_messages(chat_id):
    chat = db.session.get(Chat, chat_id) or abort(404)
    if current_user.id not in (chat.user1_id, chat.user2_id):
        abort(403)

    cleanup_old_messages()

    changed = False
    for m in chat.messages:
        if m.sender_id != current_user.id and not m.is_read:
            m.is_read = True
            changed = True
    if changed:
        db.session.commit()

    return jsonify({
        "messages": [
            {
                "id": m.id,
                "text": m.text,
                "sender_id": m.sender_id,
                "time": m.created_at.strftime("%d.%m %H:%M"),
                "is_mine": m.sender_id == current_user.id,
            }
            for m in chat.messages
        ]
    })


@app.route("/api/unread")
@login_required
def api_unread():
    chats = Chat.query.filter(
        (Chat.user1_id == current_user.id) | (Chat.user2_id == current_user.id)
    ).all()
    total = sum(c.unread_for(current_user.id) for c in chats)
    return jsonify({"unread": total})


# ---------- Профиль ----------
@app.route("/profile/<int:user_id>", methods=["GET", "POST"])
def profile(user_id):
    user = db.session.get(User, user_id) or abort(404)
    reviews = Review.query.filter_by(reviewed_id=user.id).order_by(Review.created_at.desc()).all()
    avg = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else None
    ads = Ad.query.filter_by(author_id=user.id).order_by(Ad.created_at.desc()).all()

    form = ReviewForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Войдите, чтобы оставить отзыв", "warning")
            return redirect(url_for("login", next=request.path))
        if current_user.id == user.id:
            flash("Нельзя оставить отзыв самому себе", "danger")
        else:
            db.session.add(Review(rating=form.rating.data,
                                  text=form.text.data,
                                  author_id=current_user.id,
                                  reviewed_id=user.id))
            db.session.commit()
            flash("Спасибо за отзыв!", "success")
            return redirect(url_for("profile", user_id=user.id))

    return render_template("profile.html", user=user, ads=ads,
                           reviews=reviews, avg=avg, form=form)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.phone = form.phone.data or None
        current_user.city = form.city.data or None
        current_user.is_business = form.is_business.data

        if form.avatar.data and form.avatar.data.filename:
            url = upload_to_cloudinary(form.avatar.data, folder="pomogika/avatars")
            if url:
                current_user.avatar_url = url

        db.session.commit()
        flash("Профиль обновлён", "success")
        return redirect(url_for("profile", user_id=current_user.id))

    return render_template("profile_edit.html", form=form)


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug_mode)
