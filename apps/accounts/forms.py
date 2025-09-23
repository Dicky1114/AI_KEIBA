"""
Accounts forms
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, UserPreference


class CustomUserCreationForm(UserCreationForm):
    """
    カスタムユーザー作成フォーム
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレス'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '名'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '姓'
        })
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ユーザー名'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'パスワード'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'パスワード（確認）'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """
    ユーザープロフィール編集フォーム
    """
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'profile_image', 
            'bio', 'birth_date', 'phone_number'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '自己紹介を入力してください'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '090-1234-5678'
            }),
        }


class UserPreferenceForm(forms.ModelForm):
    """
    ユーザー設定フォーム
    """
    class Meta:
        model = UserPreference
        fields = [
            'email_notifications', 'race_alerts', 'prediction_alerts',
            'default_view', 'favorite_tracks'
        ]
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'race_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prediction_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_view': forms.Select(attrs={'class': 'form-select'}),
            'favorite_tracks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '["東京", "中山", "阪神"]'
            }),
        }
