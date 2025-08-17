from rest_framework import generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, UserSerializer
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model


# Đăng ký người dùng mới
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def create(self, request, *args, **kwargs):
        # Thực hiện đăng ký người dùng bằng serializer
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # Tạo người dùng mới

            # Trả về response với isSuccess = True nếu người dùng đăng ký thành công
            return Response(
                {
                    "isSuccess": True,
                    "message": "User registered successfully",
                    "user": RegisterSerializer(
                        user
                    ).data,  # Trả về thông tin người dùng
                },
                status=200,
            )

        # Trả về lỗi nếu đăng ký không thành công
        return Response(
            {
                "isSuccess": False,
                "message": "Registration failed",
                "errors": serializer.errors,
            },
            status=400,
        )


# Xem và cập nhật thông tin người dùng
class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# Đăng nhập và nhận JWT
class LoginView(APIView):
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "isSuccess": True,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        return Response(
            {"isSuccess": False, "message": "Invalid credentials"}, status=400
        )


class RefreshTokenView(APIView):
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"message": "Refresh token is required"}, status=400)

        try:
            # Kiểm tra và làm mới refresh token cũ
            refresh = RefreshToken(refresh_token)

            # Trích xuất thông tin người dùng từ payload của refresh token
            user_id = refresh.payload.get("user_id")

            if not user_id:
                return Response(
                    {"message": "User not found in refresh token"}, status=400
                )

            # Lấy đối tượng người dùng từ user_id
            user = get_user_model().objects.get(id=user_id)

            # Tạo access token mới từ refresh token
            new_access_token = str(refresh.access_token)

            # Tạo refresh token mới cho người dùng
            new_refresh_token = RefreshToken.for_user(user)
            new_refresh_token_str = str(new_refresh_token)

            return Response(
                {
                    "isSuccess": True,
                    "access": new_access_token,  # Access token mới
                    "refresh": new_refresh_token_str,  # Refresh token mới
                }
            )
        except TokenError as e:
            return Response(
                {"isSuccess": False, "message": f"Invalid refresh token: {str(e)}"},
                status=400,
            )
        except Exception as e:
            return Response(
                {"isSuccess": False, "message": "An error occurred: " + str(e)},
                status=400,
            )


class LogoutView(APIView):
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"isSuccess": False, "message": "Refresh token is required"}, status=400
            )

        try:
            # Blacklist refresh token
            refresh = RefreshToken(refresh_token)
            refresh.blacklist()  # Đánh dấu token là không hợp lệ (blacklist)

            return Response({"isSuccess": True, "message": "Logged out successfully"})
        except TokenError as e:
            return Response(
                {"isSuccess": False, "message": f"Invalid refresh token: {str(e)}"},
                status=400,
            )
