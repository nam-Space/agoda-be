from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HotelListView,
    HotelCreateView,
    HotelDetailView,
    HotelUpdateView,
    HotelUpdateViewNotImage,
    HotelDeleteView,
    HotelImageDeleteView,
    HotelByCityView,
    HotelSearchView,
    UserHotelInteractionDetailView,
    UserHotelInteractionUpsertView,
)
from .hotel_search_views import HotelSearchAPI, RoomAvailabilityAPI
from .search_suggestions_views import SearchSuggestionsAPI
from .search_history_views import SaveSearchHistoryAPI

urlpatterns = [
    path(
        "hotels/", HotelListView.as_view(), name="hotel-list"
    ),
    path(
        "hotels/create/", HotelCreateView.as_view(), name="hotel-create"
    ),
    path(
        "hotels/<int:pk>/", HotelDetailView.as_view(), name="hotel-detail"
    ),
    path(
        "hotels/<int:pk>/update/", HotelUpdateView.as_view(), name="hotel-update"
    ),
    path(
        "hotels/<int:pk>/update/not-image/",
        HotelUpdateViewNotImage.as_view(),
        name="hotel-update-not-image",
    ),
    path(
        "hotels/<int:pk>/", HotelDetailView.as_view(), name="hotel-detail"
    ),
    path(
        "user-hotel-interaction/<int:hotel_id>/",
        UserHotelInteractionDetailView.as_view(),
        name="user-hotel-interaction-detail",
    ),
    path(
        "user-hotel-interaction/upsert/",
        UserHotelInteractionUpsertView.as_view(),
        name="user-hotel-interaction-upsert",
    ),
    path(
        "hotels/<int:pk>/delete/", HotelDeleteView.as_view(), name="hotel-delete"
    ),
    path(
        "hotel-images/<int:pk>/delete/",
        HotelImageDeleteView.as_view(),
        name="hotel-image-delete",
    ),
    path("by-city/<int:city_id>/", HotelByCityView.as_view(), name="hotel-by-city"),
    path(
        "search/", HotelSearchView.as_view(), name="hotel-search"
    ),
    
    path(
        "hotels/search/", HotelSearchAPI.as_view(), name="hotel-search-api"
    ),
    path(
        "hotels/<int:hotel_id>/rooms/availability/", 
        RoomAvailabilityAPI.as_view(), 
        name="room-availability"
    ),
    path(
        "search-suggestions/",
        SearchSuggestionsAPI.as_view(),
        name="search-suggestions"
    ),
    path(
        "save-search-history/",
        SaveSearchHistoryAPI.as_view(),
        name="save-search-history"
    ),
]
