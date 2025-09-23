"""
Accounts serializers
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, UserPreference


class UserSerializer(serializers.ModelSerializer):
    """
    ユーザー シリアライザー
    """
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'is_premium', 'profile_image', 'bio', 'birth_date', 'phone_number',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    ユーザー登録 シリアライザー
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password', 'password_confirm'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("パスワードが一致しません。")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user


class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    ユーザー設定 シリアライザー
    """
    class Meta:
        model = UserPreference
        fields = [
            'id', 'user', 'email_notifications', 'race_alerts', 
            'prediction_alerts', 'default_view', 'favorite_tracks',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
