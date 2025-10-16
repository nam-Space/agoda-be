from django.urls import path
from .views import FAQListView

urlpatterns = [
    path("by-city/", FAQListView.as_view(), name="faq-by-city"),
]
