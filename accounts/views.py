from rest_framework import generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .serializers import (
    RegisterSerializer,
    CreateUserSerializer,
    UserSerializer,
    UserAndPasswordSerializer,
)
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from .models import CustomUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
import math
from rest_framework import status


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
                    "data": RegisterSerializer(
                        user
                    ).data,  # Trả về thông tin người dùng
                }
            )

        # Trả về lỗi nếu đăng ký không thành công
        return Response(
            {
                "isSuccess": True,
                "message": "User registered successfully",
                "data": RegisterSerializer(user).data,  # Trả về thông tin người dùng
            }
        )


# Xem và cập nhật thông tin người dùng
class UserAccountDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve để trả về thông tin người dùng hiện tại.
        """
        instance = self.get_object()  # Lấy đối tượng người dùng hiện tại
        serializer = self.get_serializer(instance)  # Serialize thông tin người dùng

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "User account details fetched successfully",
                "data": serializer.data,  # Trả về thông tin người dùng đã serialize
            }
        )


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
                    "message": "Login successful",
                    "data": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                }
            )

        return Response(
            {
                "isSuccess": False,
                "message": "Invalid credentials",
                "data": {},
            }
        )


class RefreshTokenView(APIView):
    authentication_classes = []  # Bỏ qua tất cả các lớp xác thực
    permission_classes = []  # Không cần kiểm tra quyền

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"isSuccess": False, "message": "Refresh token is required"}, status=400
            )

        try:
            # Kiểm tra và làm mới refresh token cũ
            refresh = RefreshToken(refresh_token)

            # Trích xuất thông tin người dùng từ payload của refresh token
            user_id = refresh.payload.get("user_id")

            if not user_id:
                return Response(
                    {"isSuccess": False, "message": "User not found in refresh token"},
                    status=400,
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
                    "message": "Refresh token successfully!",
                    "data": {
                        "access": new_access_token,  # Access token mới
                        "refresh": new_refresh_token_str,  # Refresh token mới
                    },
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


# Phân trang
class UserPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    filters = {}

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")

        for field, value in request.query_params.items():
            if field not in ["current", "pageSize", "username", "email", "sort"]:
                # có thể dùng __icontains nếu muốn LIKE, hoặc để nguyên nếu so sánh bằng
                self.filters[f"{field}__icontains"] = value

            if field in ["username"]:
                self.filters[f"username"] = value

            if field in ["email"]:
                self.filters[f"email"] = value

        # Nếu không có hoặc giá trị không hợp lệ, dùng giá trị mặc định
        try:
            self.page_size = int(page_size) if page_size is not None else self.page_size
        except (ValueError, TypeError):
            self.page_size = self.page_size

        try:
            self.currentPage = (
                int(currentPage) if currentPage is not None else self.currentPage
            )
        except (ValueError, TypeError):
            self.currentPage = self.currentPage

        return self.page_size

    def get_paginated_response(self, data):

        total_count = CustomUser.objects.filter(**self.filters).count()
        total_pages = math.ceil(total_count / self.page_size)

        self.filters.clear()

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched users successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# API GET danh sách người dùng (với phân trang)
class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    pagination_class = UserPagination  # Áp dụng phân trang
    permission_classes = [
        IsAuthenticated
    ]  # Bảo vệ API, chỉ người dùng đã đăng nhập mới có quyền truy cập
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        """
        Lọc dữ liệu theo query params và join với bảng liên quan (nếu cần).
        Lọc động theo tất cả các trường trong CustomUser và join với các bảng khác.
        """
        queryset = CustomUser.objects.all()

        # Lọc dữ liệu theo các tham số query string
        filter_params = self.request.query_params
        query_filter = Q()

        # Duyệt qua các tham số query để tạo bộ lọc cho mỗi trường
        for field, value in filter_params.items():
            if (
                field != "current"
                and field != "pageSize"
                and field != "username"
                and field != "email"
                and field != "sort"
            ):  # Kiểm tra trường có tồn tại trong model CustomUser không
                query_filter &= Q(
                    **{f"{field}__icontains": value}
                )  # Thêm điều kiện lọc cho mỗi trường

            if field in ["username"]:
                query_filter &= Q(username=value)

            if field in ["email"]:
                query_filter &= Q(email=value)

        # Áp dụng lọc cho queryset
        queryset = queryset.filter(query_filter)

        sort_params = filter_params.get("sort")
        order_fields = []

        if sort_params:
            # Ví dụ: sort=avg_price-desc,avg_star-asc
            sort_list = sort_params.split(",")
            for sort_item in sort_list:
                try:
                    field, direction = sort_item.split("-")
                    if direction == "desc":
                        order_fields.append(f"-{field}")
                    else:
                        order_fields.append(field)
                except ValueError:
                    continue  # bỏ qua format không hợp lệ

        queryset = queryset.order_by(*order_fields)

        # Lấy tham số 'current' từ query string để tính toán trang
        current = self.request.query_params.get(
            "current", 1
        )  # Trang hiện tại, mặc định là trang 1
        page_size = self.request.query_params.get(
            "pageSize", 10
        )  # Số phần tử mỗi trang, mặc định là 10

        # Áp dụng phân trang
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(current)

        return page


# API GET chi tiết người dùng
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Chỉ người dùng đã đăng nhập có thể cập nhật hoặc xóa

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve để trả về response chuẩn cho việc lấy thông tin chi tiết người dùng.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Trả về response với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "User details fetched successfully",
                "data": serializer.data,  # Dữ liệu người dùng
            }
        )


# API POST tạo người dùng
class UserCreateView(generics.CreateAPIView):
    serializer_class = CreateUserSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Thực hiện đăng ký người dùng bằng serializer
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # Tạo người dùng mới

            # Trả về response với isSuccess = True nếu người dùng đăng ký thành công
            return Response(
                {
                    "isSuccess": True,
                    "message": "Create user successfully",
                    "data": CreateUserSerializer(
                        user
                    ).data,  # Trả về thông tin người dùng
                },
                status=200,
            )

        # Trả về lỗi nếu đăng ký không thành công
        return Response(
            {
                "isSuccess": False,
                "message": "Creating user failed",
                "errors": serializer.errors,
            },
            status=400,
        )


# API PUT hoặc PATCH để cập nhật thông tin người dùng
class UserUpdateView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserAndPasswordSerializer
    permission_classes = [IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới có thể sửa

    def update(self, request, *args, **kwargs):
        """
        Cập nhật thông tin người dùng, bao gồm mật khẩu nếu có.
        """
        # Kiểm tra xem người dùng có gửi mật khẩu mới không
        if "password" in request.data:
            # Nếu có mật khẩu mới, sử dụng set_password để mã hóa mật khẩu
            password = request.data.get("password")
            request.data["password"] = password  # Mật khẩu đã được chuẩn bị để cập nhật

        # Kiểm tra nếu có trường 'avatar' trong request để lưu đường dẫn ảnh vào cơ sở dữ liệu
        if "avatar" in request.data:
            avatar_url = request.data.get("avatar")  # Lấy đường dẫn ảnh từ request
            # Cập nhật trường avatar trong cơ sở dữ liệu
            request.data["avatar"] = avatar_url

        # Sử dụng phương thức `update` chuẩn của Django để cập nhật thông tin người dùng
        response = super().update(request, *args, **kwargs)

        return Response(
            {
                "isSuccess": True,
                "message": "User information updated successfully",
                "data": response.data,  # Trả về dữ liệu đã cập nhật
            }
        )


# API DELETE xóa người dùng
class UserDeleteView(generics.DestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]  # Chỉ người dùng đã đăng nhập mới có thể xóa

    def perform_destroy(self, instance):
        """
        Thực hiện soft delete: Cập nhật trường 'is_active' thành False thay vì xóa thực tế.
        """
        instance.is_active = (
            False  # Đánh dấu người dùng là không hoạt động (soft delete)
        )
        instance.save()  # Lưu thay đổi vào cơ sở dữ liệu

    def delete(self, request, *args, **kwargs):
        """
        Override phương thức delete để trả về response chuẩn.
        """
        instance = self.get_object()  # Lấy đối tượng người dùng cần xóa
        self.perform_destroy(instance)  # Thực hiện soft delete

        # Trả về response chuẩn với isSuccess và message
        return Response(
            {
                "isSuccess": True,
                "message": "User soft deleted successfully",
                "data": {},
            }
        )
