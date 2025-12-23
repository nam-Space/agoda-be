# Agoda Backend (agoda-be)

## 1. Tổng quan dự án

**Agoda Backend (agoda-be)** là hệ thống backend trung tâm của website du lịch Agoda, chịu trách nhiệm xử lý toàn bộ nghiệp vụ, dữ liệu và luồng vận hành cho một nền tảng du lịch quy mô lớn.

Backend được xây dựng bằng **Django + Python + MySQL**, cung cấp **RESTful API** cho nhiều frontend client như:

* Website khách hàng (agoda-fe)
* Trang quản trị (agoda-admin)
* Các hệ thống nội bộ khác

Dự án mô phỏng một **hệ sinh thái du lịch hoàn chỉnh**, hỗ trợ nhiều dịch vụ (khách sạn, taxi, vé máy bay, sự kiện…) và nhiều nhóm người dùng với phân quyền phức tạp.

---

## 2. Mục tiêu & phạm vi

Dự án được xây dựng nhằm:

* Thực hành **xây dựng Backend quy mô lớn** với Django
* Áp dụng **REST API chuẩn hoá**
* Xử lý **phân quyền đa vai trò (RBAC)**
* Thiết kế dữ liệu cho hệ thống du lịch thực tế
* Phục vụ mục đích **học tập, đồ án và portfolio cá nhân**

---

## 3. Công nghệ sử dụng

### 3.1 Công nghệ chính

* **Python 3**: Ngôn ngữ backend chính
* **Django**: Web framework
* **Django REST Framework (DRF)**: Xây dựng REST API
* **MySQL**: Cơ sở dữ liệu chính
* **WebSocket (Django Channels)**: Realtime chat & notification

### 3.2 Công nghệ & thư viện bổ trợ

* JWT Authentication
* Django ORM
* Pillow (xử lý ảnh)
* python-decouple (quản lý biến môi trường)
* CORS Headers

---

## 4. Kiến trúc Backend tổng thể

### 4.1 Mô hình kiến trúc

Backend được thiết kế theo mô hình **Layered Architecture**:

```
Client (Frontend)
     ↓
API Layer (Views / ViewSets)
     ↓
Service / Business Logic
     ↓
ORM (Models)
     ↓
MySQL Database
```

### 4.2 Nguyên tắc thiết kế

* Tách biệt rõ **Controller – Business Logic – Data**
* Mỗi module tương ứng một nghiệp vụ
* Dễ mở rộng thêm dịch vụ & role

---

## 5. Hệ thống người dùng & phân quyền

### 5.1 Các nhóm người dùng

Hệ thống hỗ trợ **9 nhóm người dùng**:

1. Khách hàng
2. Chủ khách sạn
3. Nhân viên khách sạn
4. Người tổ chức sự kiện
5. Tài xế taxi
6. Nhân viên vận hành chuyến bay
7. Nhân viên bán vé máy bay
8. Quản lý marketing
9. Admin

### 5.2 Cơ chế phân quyền (RBAC)

* Mỗi user gắn với role
* Kiểm soát quyền truy cập API
* Phân quyền CRUD theo từng module

---

## 6. Module chức năng chính

### 6.1 Authentication & Authorization

* Đăng ký / đăng nhập
* JWT Access & Refresh Token
* Bảo vệ API theo role

### 6.2 Khách sạn (Hotel Module)

* CRUD khách sạn
* CRUD phòng
* Quản lý lịch đặt phòng
* Thống kê doanh thu

### 6.3 Taxi Module

* Quản lý tài xế
* Quản lý chuyến đi
* Theo dõi trạng thái đơn taxi

### 6.4 Vé máy bay (Flight Module)

* Quản lý chuyến bay
* Lịch trình bay
* Quản lý vé

### 6.5 Sự kiện & hoạt động du lịch

* CRUD sự kiện
* Đặt & huỷ sự kiện
* Quản lý lịch trình

### 6.6 Booking & Order

* Tạo đơn đặt dịch vụ
* Cập nhật trạng thái đơn
* Huỷ đơn theo điều kiện

### 6.7 Blog & Marketing

* Viết blog cẩm nang du lịch
* Tạo chương trình khuyến mãi
* Gán khuyến mãi cho dịch vụ

---

## 7. Realtime với WebSocket

Backend sử dụng WebSocket để:

* Chat hỗ trợ khách hàng
* Gửi thông báo realtime
* Cập nhật trạng thái đơn hàng

Công nghệ:

* Django Channels
* Redis (nếu mở rộng)

---

## 8. Thiết kế Database

### 8.1 Các bảng chính

* User
* Role
* Hotel
* Room
* Booking
* Taxi
* Flight
* Event
* Promotion
* Blog

### 8.2 Đặc điểm

* Chuẩn hoá dữ liệu
* Quan hệ rõ ràng
* Dễ mở rộng

---

## 9. Cấu trúc thư mục

```
agoda-be/
├── apps/
│   ├── accounts/
│   ├── hotels/
│   ├── bookings/
│   ├── taxis/
│   ├── flights/
│   ├── events/
│   ├── promotions/
│   └── blogs/
├── core/
├── agoda/
├── manage.py
└── README.md
```

---

## 10. Cài đặt & chạy dự án

### 10.1 Clone repository

```bash
git clone https://github.com/nam-Space/agoda-be.git
cd agoda-be
```

### 10.2 Tạo môi trường ảo

```bash
python -m venv venv
source venv/bin/activate
```

### 10.3 Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 10.4 Cấu hình môi trường

Tạo file `.env`:

```
SECRET_KEY=your_secret_key
DEBUG=True
DB_NAME=agoda
DB_USER=root
DB_PASSWORD=123456
DB_HOST=localhost
DB_PORT=3306
```

### 10.5 Migrate & chạy server

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Server chạy tại:

```
http://localhost:8000
```

---

## 11. Bảo mật

* JWT Authentication
* Phân quyền API
* Validate dữ liệu đầu vào
* CORS kiểm soát domain

---

## 12. Hiệu năng & mở rộng

* ORM tối ưu query
* Có thể tích hợp cache
* Dễ tách thành microservice trong tương lai

---

## 13. Định hướng phát triển

* Payment Gateway
* Notification Service
* Recommendation System
* CI/CD & Docker

---

## 14. Mục đích học tập & portfolio

Dự án giúp:

* Nâng cao kỹ năng Django
* Thiết kế hệ thống lớn
* Hiểu rõ backend thực tế
* Chuẩn bị cho môi trường doanh nghiệp

---

## 15. Tác giả

**Nam Nguyen**
GitHub: [https://github.com/nam-Space](https://github.com/nam-Space)

---

## 16. License

Project phục vụ mục đích **học tập & portfolio**, không sử dụng thương mại.
