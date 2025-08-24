from django.urls import path
from .views import (
    RegisterView,
    UserAccountDetailView,
    LoginView,
    RefreshTokenView,
    LogoutView,
    UserListView,
    UserDetailView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", UserAccountDetailView.as_view(), name="user-profile"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh-token/", RefreshTokenView.as_view(), name="refresh-token"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # CRUD user
    path(
        "users/", UserListView.as_view(), name="user-list"
    ),  # GET tất cả người dùng, phân trang
    path(
        "users/create/", UserCreateView.as_view(), name="user-create"
    ),  # POST tạo người dùng
    path(
        "users/<int:pk>/", UserDetailView.as_view(), name="user-detail"
    ),  # GET chi tiết người dùng
    path(
        "users/<int:pk>/update/", UserUpdateView.as_view(), name="user-update"
    ),  # PUT/PATCH cập nhật người dùng
    path(
        "users/<int:pk>/delete/", UserDeleteView.as_view(), name="user-delete"
    ),  # DELETE xóa người dùng
]
