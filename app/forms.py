from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class ProfileUpdateForm(FlaskForm):
    name = StringField('Họ và tên', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Số điện thoại', validators=[Length(max=15)])
    picture = FileField(
        'Cập nhật ảnh đại diện',
        validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Chỉ chấp nhận ảnh dạng JPG, PNG, JPEG!')]
    )
    submit = SubmitField('Cập nhật')