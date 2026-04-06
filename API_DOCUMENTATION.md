# KHOAHOCTRUCTUYEN API Documentation

## Base URL
```
http://localhost:8000/api/
```

## Authentication
Các endpoint yêu cầu authentication sử dụng Token từ login.

### Headers required:
```
Authorization: Token YOUR_TOKEN
```

---

## 📋 Endpoints

### ==================== AUTH ====================

#### 1. Đăng ký tài khoản
**POST** `/auth/register/`

**Request:**
```json
{
    "username": "user123",
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student"  // "student" hoặc "teacher"
}
```

**Response:** `201 Created`
```json
{
    "user": {
        "id": 1,
        "username": "user123",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "profile": {
            "id": 1,
            "role": "student",
            "phone": null,
            "avatar": null,
            "bio": null
        }
    },
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

#### 2. Đăng nhập
**POST** `/auth/login/`

**Request:**
```json
{
    "username": "user123",
    "password": "password123"
}
```

**Response:** `200 OK`
```json
{
    "user": {...},
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

#### 3. Đăng xuất
**POST** `/auth/logout/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Response:** `200 OK`
```json
{
    "message": "Đăng xuất thành công"
}
```

---

#### 4. Lấy thông tin user hiện tại
**GET** `/auth/user/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Response:** `200 OK` - Thông tin user đầy đủ

---

### ==================== COURSE ====================

#### 1. Danh sách khóa học đã xuất bản
**GET** `/courses/?search=python&ordering=-id`

**Query Parameters:**
- `search`: Tìm kiếm (title, description, subject)
- `ordering`: Sắp xếp (created_at, title, price)
- `page`: Trang (mặc định 20 items/trang)

**Response:** `200 OK`
```json
{
    "count": 10,
    "next": "http://localhost:8000/api/courses/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "title": "Python Basics",
            "description": "...",
            "price": 100000,
            "is_free": false,
            "subject": {...},
            "grade": {...},
            "level": {...},
            "teacher": {...},
            "image": "http://localhost:8000/media/courses/...",
            "is_published": true,
            "lesson_count": 5
        }
    ]
}
```

---

#### 2. Chi tiết khóa học
**GET** `/courses/{id}/`

**Response:** `200 OK`
```json
{
    "id": 1,
    "title": "Python Basics",
    "description": "...",
    "price": 100000,
    "is_free": false,
    "subject": {...},
    "grade": {...},
    "level": {...},
    "teacher": {...},
    "image": "...",
    "is_published": true,
    "lessons": [...],
    "quizzes": [...],
    "enrollment_count": 5
}
```

---

#### 3. Danh sách khóa học của giáo viên (bao gồm chưa xuất bản)
**GET** `/my-courses/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Response:** `200 OK`

---

#### 4. Tạo khóa học (chỉ giáo viên)
**POST** `/courses/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Request:**
```json
{
    "title": "New Course",
    "description": "Description here",
    "price": 100000,
    "is_free": false,
    "subject": 1,
    "grade": 1,
    "level": 1,
    "image": <file>,
    "is_published": false
}
```

---

#### 5. Cập nhật khóa học (chỉ giáo viên có quyền)
**PUT/PATCH** `/courses/{id}/`

**Headers:** `Authorization: Token YOUR_TOKEN`

---

#### 6. Xóa khóa học (chỉ giáo viên)
**DELETE** `/courses/{id}/`

**Headers:** `Authorization: Token YOUR_TOKEN`

---

### ==================== LESSON ====================

#### 1. Danh sách bài học
**GET** `/courses/{course_id}/lessons/`

**Response:** `200 OK`
```json
[
    {
        "id": 1,
        "course": 1,
        "title": "Lesson 1",
        "video_url": "https://youtube.com/...",
        "video_file": null,
        "content": "...",
        "order": 1,
        "is_free_preview": false
    }
]
```

---

#### 2. Chi tiết bài học
**GET** `/lessons/{id}/`

---

#### 3. Tạo bài học
**POST** `/courses/{course_id}/lessons/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Request:**
```json
{
    "title": "Lesson Title",
    "video_url": "https://youtube.com/watch?v=...",
    "content": "Content here",
    "order": 1,
    "is_free_preview": false
}
```

---

### ==================== QUIZ & QUESTION ====================

#### 1. Danh sách quiz của khóa học
**GET** `/courses/{course_id}/quizzes/`

---

#### 2. Chi tiết quiz
**GET** `/quizzes/{id}/`

**Response:** `200 OK`
```json
{
    "id": 1,
    "course": 1,
    "lesson": null,
    "title": "Quiz 1",
    "description": "...",
    "time_limit": 600,  // seconds
    "minutes": 10,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z",
    "questions": [
        {
            "id": 1,
            "quiz": 1,
            "text": "Question text?",
            "order": 1,
            "points": 1,
            "choices": [
                {"id": 1, "text": "Option A", "is_correct": true},
                {"id": 2, "text": "Option B", "is_correct": false}
            ]
        }
    ]
}
```

---

#### 3. Danh sách câu hỏi
**GET** `/quizzes/{quiz_id}/questions/`

---

#### 4. Chi tiết câu hỏi
**GET** `/questions/{id}/`

---

#### 5. Danh sách lựa chọn
**GET** `/questions/{question_id}/choices/`

---

### ==================== ENROLLMENT & QUIZ ATTEMPT ====================

#### 1. Danh sách đăng ký của user
**GET** `/enrollments/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Response:** `200 OK`
```json
[
    {
        "id": 1,
        "user": {...},
        "course": {...},
        "created": "2024-01-01T10:00:00Z",
        "is_paid": true,
        "status": "approved"  // pending, paid, approved
    }
]
```

---

#### 2. Đăng ký khóa học
**POST** `/courses/{course_id}/enroll/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Response:** `201 Created`

---

#### 3. Bắt đầu bài quiz
**POST** `/quizzes/{quiz_id}/start/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Response:** `201 Created`
```json
{
    "id": 1,
    "user": {...},
    "quiz": {...},
    "started_at": "2024-01-01T10:00:00Z",
    "finished_at": null,
    "score": 0,
    "total_points": 0,
    "correct_answers": 0,
    "wrong_answers": 0,
    "percentage": 0.0,
    "completed": false,
    "answers": []
}
```

---

#### 4. Chi tiết attempt (lần làm bài)
**GET** `/attempts/{id}/`

**Headers:** `Authorization: Token YOUR_TOKEN`

---

#### 5. Submit đáp án
**PUT/PATCH** `/attempts/{id}/`

**Headers:** `Authorization: Token YOUR_TOKEN`

**Request:**
```json
{
    "answers": [
        {
            "question_id": 1,
            "choice_id": 2
        },
        {
            "question_id": 2,
            "choice_id": 5
        }
    ]
}
```

**Response:** `200 OK`
- Tự động tính điểm
- Cập nhật `score`, `percentage`, `completed`

---

#### 6. Danh sách lần làm quiz của user
**GET** `/my-attempts/`

**Headers:** `Authorization: Token YOUR_TOKEN`

---

### ==================== TEACHER ENDPOINTS ====================

#### 1. Danh sách học viên đăng ký
**GET** `/teacher/enrollments/`

**Headers:** `Authorization: Token YOUR_TOKEN` (Must be teacher)

---

#### 2. Kết quả quiz của học viên
**GET** `/teacher/quiz-results/`

**Headers:** `Authorization: Token YOUR_TOKEN` (Must be teacher)

---

### ==================== NOTIFICATION ====================

#### 1. Danh sách thông báo
**GET** `/notifications/`

**Headers:** `Authorization: Token YOUR_TOKEN`

---

#### 2. Đánh dấu đã đọc
**PUT** `/notifications/{id}/read/`

**Headers:** `Authorization: Token YOUR_TOKEN`

---

## 🔒 Permission & Authorization

| Endpoint | Anonymous | Student | Teacher | Admin |
|----------|-----------|---------|---------|-------|
| GET Courses | ✅ | ✅ | ✅ | ✅ |
| POST Course | ❌ | ❌ | ✅ | ✅ |
| PUT Course | ❌ | ❌ | ✅ (owner) | ✅ |
| DELETE Course | ❌ | ❌ | ✅ (owner) | ✅ |
| Enroll Course | ❌ | ✅ | ✅ | ✅ |
| Start Quiz | ❌ | ✅ (enrolled) | ✅ | ✅ |
| Create Level/Grade/Subject | ❌ | ❌ | ❌ | ✅ |
| Teacher Enrollments | ❌ | ❌ | ✅ | ✅ |

---

## 📝 Error Responses

### 400 Bad Request
```json
{
    "error": "Username đã tồn tại"
}
```

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
    "error": "Bạn chưa đăng ký khóa học này"
}
```

### 404 Not Found
```json
{
    "detail": "Not found."
}
```

---

## 🧪 Cách test API

### 1. Sử dụng cURL
```bash
# Đăng ký
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "role": "student"
  }'

# Đăng nhập
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'

# Lấy danh sách khóa học (với token)
curl -X GET http://localhost:8000/api/courses/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### 2. Sử dụng Django REST Framework BrowsableAPI
Mở browser vào: `http://localhost:8000/api/`

### 3. Sử dụng Postman
- Import: `http://localhost:8000/api/`
- Set Authorization: Bearer Token

### 4. Sử dụng Python requests
```python
import requests

# Đăng nhập
response = requests.post('http://localhost:8000/api/auth/login/', json={
    'username': 'testuser',
    'password': 'password123'
})
token = response.json()['token']

# Lấy danh sách khóa học
headers = {'Authorization': f'Token {token}'}
response = requests.get('http://localhost:8000/api/courses/', headers=headers)
print(response.json())
```

---

## 🔗 Links

- Admin: `http://localhost:8000/admin/`
- API Root: `http://localhost:8000/api/`
- Web: `http://localhost:8000/`
