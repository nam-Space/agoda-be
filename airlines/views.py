from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
from .models import Airline, Aircraft
from .serializers import AirlineSerializer, AircraftSerializer, AirlineCreateSerializer
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q


# Phân trang chung cho Airline và Aircraft
class CommonPagination(PageNumberPagination):
    page_size = 10
    page_query_param = "current"
    page_size_query_param = "pageSize"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "isSuccess": True,
                "message": self.context.get("message", "Fetched data successfully!"),
                "meta": {
                    "totalItems": self.page.paginator.count,
                    "currentPage": self.page.number,
                    "itemsPerPage": self.get_page_size(self.request),
                    "totalPages": self.page.paginator.num_pages,
                },
                "data": data,
            }
        )


class AirlineListView(generics.ListCreateAPIView):
    serializer_class = AirlineSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = CommonPagination

    def get_serializer_class(self):
        # POST → dùng serializer khác
        if self.request.method == "POST":
            return AirlineCreateSerializer
        # GET → serializer mặc định
        return AirlineSerializer

    def get_queryset(self):
        queryset = Airline.objects.all().order_by("-id")
        filter_params = self.request.query_params
        query_filter = Q()

        # Duyệt qua các tham số query để tạo bộ lọc cho mỗi trường
        for field, value in filter_params.items():
            if (
                field != "current"
                and field != "pageSize"
                and field != "page"
                and field != "page_size"
                and field != "sort"
                and field != "flight_operations_staff_id"
            ):
                query_filter &= Q(
                    **{f"{field}__icontains": value}
                )  # Thêm điều kiện lọc cho mỗi trường

            if field == "flight_operations_staff_id":
                query_filter &= Q(**{f"{field}": value})

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

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Truyền message vào context để phân trang trả về đúng message
            self.paginator.context = {"message": "Fetched all airlines successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all airlines successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            airline = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Airline created successfully",
                    "data": AirlineSerializer(airline).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create airline",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class AirlineDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer
    authentication_classes = []
    permission_classes = []

    def get_serializer_class(self):
        # PUT / PATCH / DELETE → dùng AirlineCreateSerializer
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return AirlineCreateSerializer
        # GET → dùng AirlineSerializer
        return AirlineSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Airline details fetched successfully",
                "data": serializer.data,
            }
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Airline updated successfully",
                    "data": serializer.data,
                }
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update airline",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Airline deleted successfully",
            },
            status=status.HTTP_200_OK,
        )


class AircraftListView(generics.ListCreateAPIView):
    serializer_class = AircraftSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = CommonPagination

    def get_queryset(self):
        queryset = (
            Aircraft.objects.select_related("airline").all().order_by("-created_at")
        )
        filter_params = self.request.query_params
        airline_id = filter_params.get("airline_id")
        if airline_id:
            queryset = queryset.filter(airline_id=airline_id)

        flight_operations_staff_id = filter_params.get("flight_operations_staff_id")
        if flight_operations_staff_id:
            queryset = queryset.filter(
                airline__flight_operations_staff_id=flight_operations_staff_id
            )

        model = filter_params.get("model")
        if model:
            queryset = queryset.filter(model__icontains=model)

        registration_number = filter_params.get("registration_number")
        if registration_number:
            queryset = queryset.filter(
                registration_number__icontains=registration_number
            )

        is_active = filter_params.get("is_active")
        if is_active:
            queryset = queryset.filter(is_active=is_active)

        manufacture_year = filter_params.get("manufacture_year")
        if manufacture_year:
            queryset = queryset.filter(manufacture_year=manufacture_year)

        min_total_seats = filter_params.get("min_total_seats")
        if min_total_seats:
            queryset = queryset.filter(total_seats__gte=min_total_seats)

        max_total_seats = filter_params.get("max_total_seats")
        if max_total_seats:
            queryset = queryset.filter(total_seats__lte=max_total_seats)

        min_economy_seats = filter_params.get("min_economy_seats")
        if min_economy_seats:
            queryset = queryset.filter(economy_seats__gte=min_economy_seats)

        max_economy_seats = filter_params.get("max_economy_seats")
        if max_economy_seats:
            queryset = queryset.filter(economy_seats__lte=max_economy_seats)

        min_business_seats = filter_params.get("min_business_seats")
        if min_business_seats:
            queryset = queryset.filter(business_seats__gte=min_business_seats)

        max_business_seats = filter_params.get("max_business_seats")
        if max_business_seats:
            queryset = queryset.filter(business_seats__lte=max_business_seats)

        min_first_class_seats = filter_params.get("min_first_class_seats")
        if min_first_class_seats:
            queryset = queryset.filter(first_class_seats__gte=min_first_class_seats)

        max_first_class_seats = filter_params.get("max_first_class_seats")
        if max_first_class_seats:
            queryset = queryset.filter(first_class_seats__lte=max_first_class_seats)

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

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            self.paginator.context = {"message": "Fetched all aircrafts successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all aircrafts successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            aircraft = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Aircraft created successfully",
                    "data": AircraftSerializer(aircraft).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to create aircraft",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class AircraftDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Aircraft.objects.select_related("airline").all()
    serializer_class = AircraftSerializer
    authentication_classes = []
    permission_classes = []

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Aircraft details fetched successfully",
                "data": serializer.data,
            }
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Aircraft updated successfully",
                    "data": serializer.data,
                }
            )
        return Response(
            {
                "isSuccess": False,
                "message": "Failed to update aircraft",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Aircraft deleted successfully",
            },
            status=status.HTTP_200_OK,
        )
