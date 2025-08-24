from rest_framework import serializers
from django.contrib.auth import get_user_model


# Serializer cho việc đăng ký người dùng mới
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "birthday",
            "phone_number",
            "gender",
            "role",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "birthday": {"required": False},
        }

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=validated_data["password"],
            birthday=validated_data.get("birthday", None),
            phone_number=validated_data["phone_number"],
            gender=validated_data["gender"],
            role=validated_data["role"],
        )
        return user


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "birthday",
            "phone_number",
            "gender",
            "role",
            "avatar",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "birthday": {"required": False},
            "avatar": {"required": False},
        }

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=validated_data["password"],
            birthday=validated_data.get("birthday", None),
            phone_number=validated_data["phone_number"],
            gender=validated_data["gender"],
            role=validated_data["role"],
            avatar=validated_data["avatar"],
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
            "first_name",
            "last_name",
            "birthday",
            "phone_number",
            "gender",
            "role",
            "avatar",
            "is_active",
            "date_joined",
        ]
        extra_kwargs = {"birthday": {"required": False}}


# Serializer cho thông tin người dùng (có mật khẩu)
class UserAndPasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)  # Không bắt buộc

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "birthday",
            "phone_number",
            "gender",
            "role",
            "avatar",
            "is_active",
            "date_joined",
            "password",
        ]
        extra_kwargs = {"birthday": {"required": False}}

    def update(self, instance, validated_data):
        """
        Cập nhật thông tin người dùng, bao gồm mật khẩu (nếu có).
        """
        password = validated_data.pop(
            "password", None
        )  # Lấy mật khẩu từ validated_data nếu có

        # Nếu có mật khẩu, mã hóa và lưu
        if password:
            instance.set_password(password)

        # Cập nhật các trường còn lại
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()  # Lưu lại đối tượng
        return instance


class AvatarImageSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField()  # Đảm bảo xử lý ImageField đúng cách

    class Meta:
        model = get_user_model()
        fields = ["avatar"]
        read_only_fields = ["avatar"]  # Không cho phép cập nhật trực tiếp ngoài API
