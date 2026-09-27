from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, TextAreaField, IntegerField,
                     SelectField, BooleanField, SubmitField)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

CATEGORIES = [
    "Дом и быт",
    "Обучение",
    "Цифровое",
    "Курьер",
    "Ремонт",
    "Творчество",
    "Бизнес-помощь",
]


class RegisterForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6)])
    phone = StringField("Телефон")
    city = StringField("Город")
    is_business = BooleanField("Я представляю бизнес")
    submit = SubmitField("Зарегистрироваться")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")


class AdForm(FlaskForm):
    type = SelectField(
        "Тип объявления",
        choices=[
            ("pomosch", "Помощь — разовая задача (около 1 часа)"),
            ("podrabotka", "Подработка — на целый день (оплата за час)"),
        ],
        validators=[DataRequired()],
    )
    title = StringField("Что нужно сделать",
                        validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField("Подробное описание",
                                validators=[DataRequired(), Length(min=5)])
    category = SelectField("Категория",
                           choices=[(c, c) for c in CATEGORIES],
                           validators=[DataRequired()])
    price = IntegerField("Цена, ₽", validators=[DataRequired(), NumberRange(min=0)])
    city = StringField("Город", validators=[DataRequired()])
    address = StringField("Адрес (необязательно)")
    photos = FileField(
        "Фото (можно несколько)",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Только изображения")],
    )
    submit = SubmitField("Опубликовать")


class ProfileForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField("Телефон", validators=[Optional()])
    city = StringField("Город", validators=[Optional()])
    is_business = BooleanField("Я представляю бизнес")
    avatar = FileField(
        "Аватарка",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Только изображения")],
    )
    submit = SubmitField("Сохранить")


class ReviewForm(FlaskForm):
    rating = SelectField("Оценка",
                         choices=[(i, str(i)) for i in range(5, 0, -1)],
                         coerce=int)
    text = TextAreaField("Отзыв", validators=[DataRequired(), Length(min=2)])
    submit = SubmitField("Отправить")