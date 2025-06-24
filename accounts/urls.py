from django.urls import path
from .views import RegisterView, UserDetailView, LoginView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", UserDetailView.as_view(), name="user-profile"),
    path("login/", LoginView.as_view(), name="login"),
]
