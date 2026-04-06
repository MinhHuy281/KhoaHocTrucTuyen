# KhoaHocTrucTuyen

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**KhoaHocTrucTuyen** là nền tảng học trực tuyến (e-learning) được xây dựng bằng **Django**, hỗ trợ học viên, giảng viên và quản trị viên. Hệ thống cho phép quản lý khóa học, video bài giảng, bài tập ôn luyện, thanh toán và tương tác Q&A.

## Mục tiêu dự án
Xây dựng một website học trực tuyến đơn giản, thân thiện, phù hợp cho học sinh tiểu học đến trung học, với giao diện dễ sử dụng và quản lý nội dung linh hoạt.

## Vai trò người dùng (Roles)

| Vai trò              | Mô tả                                                                 | Quyền hạn chính                                                                 |
|----------------------|-----------------------------------------------------------------------|---------------------------------------------------------------------------------|
| **Admin**            | Quản trị viên hệ thống                                                | Quản lý tài khoản, phân quyền, quản lý khóa học, danh mục môn/lớp/cấp, thống kê & báo cáo |
| **User (Học viên / Giảng viên)** | Người dùng đã đăng ký và đăng nhập                                    | Học viên: Đăng ký khóa học, xem video, tài liệu, làm bài tập, theo dõi tiến độ<br>Giảng viên: Quản lý khóa học, video, bài tập, theo dõi học viên |
| **Guest**            | Người dùng chưa đăng ký                                               | Xem thông tin khóa học, tìm kiếm, truy cập trang chủ và đăng ký tài khoản     |

## Các tính năng chính

| Module           | Tính năng                                     | Priority    | Sprint   |
|------------------|-----------------------------------------------|-------------|----------|
| Auth             | Đăng ký, Đăng nhập, Quên mật khẩu             | Must have   | Sprint 1 |
| User Profile     | Cập nhật thông tin cá nhân                    | Must have   | Sprint 1 |
| Course           | Xem danh sách khóa học theo môn/lớp/cấp       | Must have   | Sprint 1 |
| Course           | Tìm kiếm khóa học                             | Must have   | Sprint 1 |
| Admin            | Quản lý tài khoản người dùng                  | Must have   | Sprint 1 |
| Admin            | Phân quyền người dùng                         | Must have   | Sprint 1 |
| Enrollment       | Đăng ký / kích hoạt khóa học                  | Must have   | Sprint 2 |
| Learning Content | Xem video bài giảng                           | Must have   | Sprint 2 |
| Instructor       | Tạo khóa học mới                              | Must have   | Sprint 2 |
| Instructor       | Cập nhật / chỉnh sửa thông tin khóa học       | Must have   | Sprint 2 |
| Instructor       | Quản lý video bài giảng                       | Must have   | Sprint 2 |
| Instructor       | Theo dõi danh sách học viên trong khóa        | Should have | Sprint 2 |
| Payment          | Thanh toán khóa học                           | Must have   | Sprint 2 |
| Support          | Liên hệ Zalo hỗ trợ                           | Should have | Sprint 2 |
| Admin            | Quản lý danh mục môn học, lớp học             | Must have   | Sprint 2 |
| Admin            | Quản lý khóa học                              | Must have   | Sprint 2 |
| Exercise         | Làm bài tập ôn luyện                          | Must have   | Sprint 3 |
| Exercise         | Xem điểm số và kết quả làm bài                | Should have | Sprint 3 |
| Q&A              | Gửi câu hỏi cho giảng viên                    | Should have | Sprint 3 |
| Q&A              | Giảng viên trả lời thắc mắc học viên          | Should have | Sprint 3 |
| Instructor       | Tạo bài tập và cập nhật đáp án                | Must have   | Sprint 3 |
| Admin            | Quản lý thanh toán                            | Should have | Sprint 3 |
| Admin            | Thống kê và báo cáo hệ thống                  | Must have   | Sprint 4 |

## Công nghệ sử dụng

- **Backend**: Django 5.2
- **Database**: SQLite (dev) / PostgreSQL (production khuyến nghị)
- **Frontend**: HTML, CSS, Bootstrap (hoặc Tailwind nếu nâng cấp)
- **Authentication**: Django built-in auth + custom views
- **Storage**: Local media cho video/ảnh (dev), có thể dùng S3/Cloudinary sau
- **Other**: Python 3.10+, timezone Asia/Ho_Chi_Minh

## Cài đặt & Chạy dự án (Local Development)

### Yêu cầu
- Python 3.10+
- Git
- Virtualenv (khuyến nghị)
- MySQL Server 8.0+ (hoặc MariaDB tương thích)

### Các bước cài đặt

1. Clone repository

```bash
git clone https://github.com/MinhHuy281/KhoaHocTrucTuyen.git
cd KhoaHocTrucTuyen
```

2. Tạo và kích hoạt môi trường ảo

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows (CMD):

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Cài đặt dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Tạo database MySQL

```sql
CREATE DATABASE khoahoctructuyen CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

5. Cấu hình database trong [KhoaHocTrucTuyen/settings.py](KhoaHocTrucTuyen/settings.py)

Cập nhật các giá trị trong DATABASES['default'] cho đúng máy local của bạn:
- NAME: khoahoctructuyen
- USER
- PASSWORD
- HOST
- PORT

6. Chạy migrate

```bash
python manage.py migrate
```

7. Tạo tài khoản admin (khuyến nghị)

```bash
python manage.py createsuperuser
```

8. Chạy server local

```bash
python manage.py runserver
```

Truy cập:
- Trang web: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

### Chạy kiểm thử

```bash
python manage.py test
```

### Ghi chú cho chức năng quên mật khẩu
- Mặc định đang dùng console email backend để test local.
- Mã xác nhận reset password sẽ in ra terminal đang chạy server.
