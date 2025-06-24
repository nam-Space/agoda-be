from rest_framework import serializers
from django.contrib.auth import get_user_model


# Serializer cho việc đăng ký người dùng mới
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "email",
            "password",
            "birthday",
            "phone_number",
            "gender",
            "role",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            birthday=validated_data["birthday"],
            phone_number=validated_data["phone_number"],
            gender=validated_data["gender"],
            role=validated_data["role"],
        )
        return user


# Serializer cho thông tin người dùng
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "birthday",
            "phone_number",
            "gender",
            "role",
        ]
