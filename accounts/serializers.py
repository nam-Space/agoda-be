from rest_framework import serializers
from django.contrib.auth import get_user_model

# from hotels.serializers import HotelSerializer


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
    manager = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )

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
            "manager",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "birthday": {"required": False},
            "avatar": {"required": False},
            "manager": {"required": False},
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = get_user_model()(**validated_data)

        if password:
            user.set_password(password)

        user.save()
        return user


class UserStaffSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "avatar",
            "role",
            "gender",
            "phone_number",
            "birthday",
        ]


class UserSimpleSerializer(serializers.ModelSerializer):
    hotel = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "avatar",
            "role",
            "gender",
            "phone_number",
            "birthday",
            "hotel",
        ]

    def get_hotel(self, obj):
        # import lazy để tránh circular import
        from hotels.serializers import HotelSimpleSerializer

        if hasattr(obj, "hotel") and obj.hotel:
            return HotelSimpleSerializer(obj.hotel).data
        return None


# Serializer cho thông tin người dùng
class UserSerializer(serializers.ModelSerializer):
    hotel = serializers.SerializerMethodField()
    manager = UserSimpleSerializer(read_only=True)  # quản lý
    staffs = UserStaffSimpleSerializer(many=True, read_only=True)  # nhân viên

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
            "hotel",
            "manager",  # 🆕 thêm trường quản lý
            "staffs",  # 🆕 thêm danh sách nhân viên
        ]
        extra_kwargs = {"birthday": {"required": False}}

    def get_hotel(self, obj):
        # import lazy để tránh circular import
        from hotels.serializers import HotelSimpleSerializer

        if hasattr(obj, "hotel") and obj.hotel:
            return HotelSimpleSerializer(obj.hotel).data
        return None


# Serializer cho thông tin người dùng (có mật khẩu)
class UserAndPasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)  # Không bắt buộc
    manager = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )

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
            "manager",
        ]
        extra_kwargs = {
            "birthday": {"required": False},
            "manager": {"required": False},
        }

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        if password:
            instance.set_password(password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class AvatarImageSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField()  # Đảm bảo xử lý ImageField đúng cách

    class Meta:
        model = get_user_model()
        fields = ["avatar"]
        read_only_fields = ["avatar"]  # Không cho phép cập nhật trực tiếp ngoài API
