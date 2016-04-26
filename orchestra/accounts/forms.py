from django import forms
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class UserForm(forms.ModelForm):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()

    class Meta:
        model = UserModel
        fields = ('first_name', 'last_name', 'email')
        exclude = ('is_staff', 'is_active', 'date_joined', 'username')
