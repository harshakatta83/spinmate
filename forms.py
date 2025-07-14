from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, FloatField, DateField, TimeField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional
from datetime import date, timedelta, datetime

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')])
    address = TextAreaField('Address', validators=[DataRequired()])
    submit = SubmitField('Register')

class OrderForm(FlaskForm):
    pickup_address = TextAreaField('Pickup Address', validators=[DataRequired()])
    delivery_address = TextAreaField('Delivery Address', validators=[DataRequired()])
    pickup_date = DateField('Pickup Date', validators=[DataRequired()], default=date.today() + timedelta(days=1))
    pickup_time = TimeField('Pickup Time', validators=[DataRequired()], default=datetime.now().time())
    special_instructions = TextAreaField('Special Instructions', validators=[Length(max=500)])
    eco_wash = BooleanField('Eco-Friendly Wash')
    pincode = StringField('Pincode', validators=[DataRequired(), Length(min=6, max=6, message="Pincode must be 6 digits")])
    submit = SubmitField('NEXT')

class OrderItemForm(FlaskForm):
    service_id = SelectField('Service Type', coerce=int, validators=[DataRequired()])
    item_name = StringField('Item Name', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    weight = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=0)], 
                       description='Required for weight-based services like Express Laundry')
    fabric_type = SelectField('Fabric Type', validators=[Optional()],
                             choices=[('', 'Select Fabric Type'),
                                    ('cotton', 'Cotton'),
                                    ('silk', 'Silk'),
                                    ('wool', 'Wool'),
                                    ('synthetic', 'Synthetic'),
                                    ('denim', 'Denim'),
                                    ('delicate', 'Delicate'),
                                    ('leather', 'Leather')])
    stain_notes = TextAreaField('Stain Notes', validators=[Optional()], 
                               description='Describe any stains or special care needed')

class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    address = TextAreaField('Address', validators=[DataRequired()])
    submit = SubmitField('Update Profile')

class StatusUpdateForm(FlaskForm):
    status = SelectField('Status', validators=[DataRequired()],
                        choices=[('pending', 'Pending'),
                               ('picked', 'Picked Up'),
                               ('washing', 'Washing'),
                               ('ready', 'Ready for Delivery'),
                               ('delivered', 'Delivered'),
                               ('cancelled', 'Cancelled')])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Update Status')

class FeedbackForm(FlaskForm):
    rating = SelectField('Rating', validators=[DataRequired()], coerce=int,
                        choices=[(5, '5 - Excellent'), (4, '4 - Good'), 
                               (3, '3 - Average'), (2, '2 - Poor'), (1, '1 - Very Poor')])
    comment = TextAreaField('Comment', validators=[Optional()])
    submit = SubmitField('Submit Feedback')

class PincodeForm(FlaskForm):
    pincode = StringField('Pincode', validators=[DataRequired(), Length(min=6, max=6, message="Pincode must be 6 digits")])
    submit_pincode = SubmitField('Check Pincode')
