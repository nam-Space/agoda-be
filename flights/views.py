from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from rest_framework.response import Response
from datetime import datetime
from .models import Flight, FlightLeg, FlightBookingDetail, SeatClassPricing
from .serializers import (
    FlightBookingDetailSerializer,
    FlightLegSerializer,
    FlightSerializer,
    SeatClassPricingSerializer,
    FlightLegGetListSerializer,
    SeatClassPricingGetListSerializer,
    FlightGetListSerializer,
)
from rest_framework import status
from django.db.models import Q
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import generics


class CommonPagination(PageNumberPagination):
    page_size = 10
    page_query_param = "current"
    page_size_query_param = "pageSize"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "isSuccess": True,
                "message": self.context.get("message", "Fetched flights successfully!"),
                "meta": {
                    "totalItems": self.page.paginator.count,
                    "currentPage": self.page.number,
                    "itemsPerPage": self.get_page_size(self.request),
                    "totalPages": self.page.paginator.num_pages,
                },
                "data": data,
            }
        )


class FlightListView(generics.ListAPIView):
    serializer_class = FlightGetListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    pagination_class = CommonPagination

    def get_queryset(self):
        queryset = Flight.objects.all()
        filter_params = self.request.query_params
        query_filter = Q()

        # Duyệt qua các tham số query để tạo bộ lọc cho mỗi trường
        for field, value in filter_params.items():
            if (
                field != "current"
                and field != "pageSize"
                and field != "sort"
                and field != "airline_id"
                and field != "flight_operations_staff_id"
            ):
                query_filter &= Q(
                    **{f"{field}__icontains": value}
                )  # Thêm điều kiện lọc cho mỗi trường
            if field == "airline_id":
                query_filter &= Q(**{f"{field}": value})
            if field == "flight_operations_staff_id":
                query_filter &= Q(**{f"airline__flight_operations_staff_id": value})

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
            self.paginator.context = {"message": "Fetched all flights successfully!"}
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all flights successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )


class FlightViewSet(viewsets.ModelViewSet):
    queryset = (
        Flight.objects.select_related("airline", "aircraft", "aircraft__airline")
        .prefetch_related(
            "legs__departure_airport", "legs__arrival_airport", "seat_classes"
        )
        .all()
        .order_by("-id")
    )
    serializer_class = FlightSerializer
    pagination_class = CommonPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params

        # Filter theo baggage included
        baggage_included = q.get("baggageIncluded")
        if baggage_included and baggage_included.lower() == "true":
            queryset = queryset.filter(baggage_included=True)

        # Filter theo airline (có thể multiple airlines)
        airlines = q.getlist("airlines[]") or [q.get("airline")]
        airlines = [a for a in airlines if a]  # Remove None/empty
        if airlines:
            queryset = queryset.filter(airline_id__in=airlines)

        # Filter theo số điểm dừng (có thể multiple)
        stops_list = q.getlist("stops[]")
        if stops_list:
            # Convert labels to numbers: "Bay Thẳng"=0, "1 Điểm Dừng"=1, ">2 Điểm Dừng"=2+
            stops_values = []
            for stop in stops_list:
                if stop == "0" or stop == "Bay Thẳng":
                    stops_values.append(0)
                elif stop == "1" or stop == "1 Điểm Dừng":
                    stops_values.append(1)
                elif stop == ">2" or stop == ">2 Điểm Dừng":
                    # Lọc flights có >= 2 stops
                    pass

            if stops_values:
                queryset = queryset.filter(stops__in=stops_values)
            # Handle >2 stops
            if any(s in [">2", ">2 Điểm Dừng"] for s in stops_list):
                queryset = queryset.filter(stops__gte=2)

        # Filter theo hạng ghế (có thể multiple)
        seat_classes = q.getlist("seatClasses[]") or [q.get("seatClass")]
        seat_classes = [sc for sc in seat_classes if sc]
        if seat_classes:
            queryset = queryset.filter(
                seat_classes__seat_class__in=seat_classes,
                seat_classes__available_seats__gt=0,
            ).distinct()

        # Filter theo max duration (minutes)
        max_duration = q.get("maxDuration")
        if max_duration:
            queryset = queryset.filter(total_duration__lte=int(max_duration))

        # Filter theo max price
        max_price = q.get("maxPrice")
        if max_price:
            queryset = queryset.filter(base_price__lte=float(max_price))

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        q = request.query_params

        # Lấy params để filter thêm
        origin = q.get("origin")
        destination = q.get("destination")
        departure_date = q.get("departureDate")
        departure_hour = q.get("departureHour")  # 0-24
        arrival_hour = q.get("arrivalHour")  # 0-24

        # Filter theo origin, destination, departure_date, hours
        filtered_flights = []
        for flight in queryset:
            legs = list(flight.legs.order_by("departure_time"))
            if not legs:
                continue

            first_leg = legs[0]
            last_leg = legs[-1]

            # Check origin
            if origin and str(first_leg.departure_airport_id) != origin:
                continue

            # Check destination
            if destination and str(last_leg.arrival_airport_id) != destination:
                continue

            # Check departure date
            if departure_date:
                try:
                    date_obj = datetime.strptime(departure_date, "%Y-%m-%d").date()
                    if first_leg.departure_time.date() != date_obj:
                        continue
                except ValueError:
                    pass

            # Check departure hour
            if departure_hour:
                dep_hour = first_leg.departure_time.hour
                target_hour = int(departure_hour)
                if dep_hour < target_hour:
                    continue

            # Check arrival hour
            if arrival_hour:
                arr_hour = last_leg.arrival_time.hour
                target_hour = int(arrival_hour)
                if arr_hour < target_hour:
                    continue

            filtered_flights.append(flight)

        # Sort if needed
        sort_by = q.get("sortBy")
        if sort_by == "price_asc":
            filtered_flights.sort(key=lambda f: f.base_price)
        elif sort_by == "price_desc":
            filtered_flights.sort(key=lambda f: f.base_price, reverse=True)
        elif sort_by == "duration_asc":
            filtered_flights.sort(key=lambda f: f.total_duration)
        elif sort_by == "duration_desc":
            filtered_flights.sort(key=lambda f: f.total_duration, reverse=True)

        # Paginate
        page = self.paginate_queryset(filtered_flights)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            self.paginator.context = {"message": "Fetched flights successfully!"}
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered_flights, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched flights successfully!",
                "meta": {"totalItems": len(filtered_flights), "pagination": None},
                "data": serializer.data,
            }
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        q = self.request.query_params

        context["origin"] = q.get("origin")
        context["destination"] = q.get("destination")
        context["departureDate"] = q.get("departureDate")
        context["seatClass"] = q.get("seatClass")
        context["airline"] = q.get("airline")
        context["stops"] = q.get("stops")

        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched flight details successfully!",
                "data": serializer.data,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            flight = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Flight created successfully!",
                    "data": self.get_serializer(flight).data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Failed to create flight.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            flight = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Flight updated successfully!",
                    "data": self.get_serializer(flight).data,
                }
            )
        else:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Failed to update flight.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Flight deleted successfully!",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )


class FlightLegViewSet(viewsets.ModelViewSet):
    # queryset = FlightLeg.objects.select_related(
    #     "departure_airport", "arrival_airport", "flight", "flight__airline"
    # ).all()
    # serializer_class = FlightLegSerializer

    # serializer_class = FlightLegSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    pagination_class = CommonPagination

    # ⭐ Chọn serializer theo action
    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return FlightLegGetListSerializer
        return FlightLegSerializer

    def get_queryset(self):
        queryset = FlightLeg.objects.select_related(
            "departure_airport", "arrival_airport", "flight", "flight__airline"
        ).all()
        filter_params = self.request.query_params
        query_filter = Q()

        # Duyệt qua các tham số query để tạo bộ lọc cho mỗi trường
        for field, value in filter_params.items():
            if (
                field != "current"
                and field != "pageSize"
                and field != "sort"
                and field != "flight_id"
            ):
                query_filter &= Q(
                    **{f"{field}__icontains": value}
                )  # Thêm điều kiện lọc cho mỗi trường

            if field in ["flight_id"]:
                query_filter &= Q(flight_id=value)

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

        serializer = self.get_serializer(
            page if page is not None else queryset, many=True
        )

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Truyền message vào context để phân trang trả về đúng message
            self.paginator.context = {
                "message": "Fetched all flight legs successfully!"
            }
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all flight legs successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched flight leg details successfully!",
                "data": serializer.data,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            flight_leg = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Flight leg created successfully!",
                    "data": self.get_serializer(flight_leg).data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Failed to create flight leg.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            flight_leg = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Flight leg updated successfully!",
                    "data": self.get_serializer(flight_leg).data,
                }
            )
        else:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Failed to update flight leg.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Flight leg deleted successfully!",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )


class SeatClassPricingViewSet(viewsets.ModelViewSet):
    # queryset = SeatClassPricing.objects.select_related("flight").all()
    # serializer_class = SeatClassPricingSerializer

    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     flight_id = self.request.query_params.get("flight_id")
    #     if flight_id:
    #         queryset = queryset.filter(flight_id=flight_id)
    #     return queryset

    # serializer_class = SeatClassPricingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = []
    pagination_class = CommonPagination

    # ⭐ Chọn serializer theo action
    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return SeatClassPricingGetListSerializer
        return SeatClassPricingSerializer

    def get_queryset(self):
        queryset = SeatClassPricing.objects.select_related("flight").all()
        filter_params = self.request.query_params
        query_filter = Q()

        # Duyệt qua các tham số query để tạo bộ lọc cho mỗi trường
        for field, value in filter_params.items():
            if (
                field != "current"
                and field != "pageSize"
                and field != "flight_id"
                and field != "sort"
            ):
                query_filter &= Q(
                    **{f"{field}__icontains": value}
                )  # Thêm điều kiện lọc cho mỗi trường
            if field in ["flight_id"]:
                query_filter &= Q(flight_id=value)

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

        serializer = self.get_serializer(
            page if page is not None else queryset, many=True
        )

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Truyền message vào context để phân trang trả về đúng message
            self.paginator.context = {
                "message": "Fetched all flight legs successfully!"
            }
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched all flight legs successfully!",
                "meta": {"totalItems": queryset.count(), "pagination": None},
                "data": serializer.data,
            }
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "isSuccess": True,
                "message": "Fetched seat class details successfully!",
                "data": serializer.data,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            seat_class_pricing = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Seat class created successfully!",
                    "data": self.get_serializer(seat_class_pricing).data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Failed to create seat class.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            seat_class_pricing = serializer.save()
            return Response(
                {
                    "isSuccess": True,
                    "message": "Seat class updated successfully!",
                    "data": self.get_serializer(seat_class_pricing).data,
                }
            )
        else:
            return Response(
                {
                    "isSuccess": False,
                    "message": "Failed to update seat class.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {
                "isSuccess": True,
                "message": "Seat class deleted successfully!",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )


class FlightBookingDetailViewSet(viewsets.ModelViewSet):
    queryset = FlightBookingDetail.objects.select_related("booking", "flight").all()
    serializer_class = FlightBookingDetailSerializer
