# images/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.core.files.storage import default_storage
import os


class UploadImageView(APIView):
    permission_classes = [IsAuthenticated]  # Chỉ cho phép người dùng đã đăng nhập
    parser_classes = [MultiPartParser, FormParser]  # Để nhận file hình ảnh từ form-data

    def post(self, request, *args, **kwargs):
        # Lấy tham số 'type' từ query string để xác định loại đối tượng (user, hotel, room)
        image_type = request.query_params.get("type", "")
        file = request.FILES.get("image")  # Tên tham số file sẽ là 'image'

        if not file:
            return Response(
                {"isSuccess": False, "message": "No image file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lưu ảnh vào thư mục cục bộ
        file_path = default_storage.save(f"{image_type}_images/{file.name}", file)

        # Lấy URL để trả về cho người dùng
        image_url = os.path.join(settings.MEDIA_URL, file_path)

        return Response(
            {
                "isSuccess": True,
                "message": f"{image_type.capitalize()} image uploaded successfully",
                "data": {"image_url": image_url},
            },
            status=status.HTTP_200_OK,
        )
