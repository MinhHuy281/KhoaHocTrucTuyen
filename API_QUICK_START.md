# 🚀 QUICK START - API Usage

## Base URL
```
http://localhost:8000/api/
```

---

## 1️⃣ Đăng Ký Tài Khoản

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "email": "student1@example.com",
    "password": "password123",
    "first_name": "Student",
    "last_name": "One",
    "role": "student"
  }'
```

**Response:**
```json
{
    "user": {
        "id": 1,
        "username": "student1",
        "email": "student1@example.com",
        "first_name": "Student",
        "last_name": "One",
        "profile": {"id": 1, "role": "student"}
    },
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

## 2️⃣ Đăng Nhập

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "password": "password123"
  }'
```

**Response:**
```json
{
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

## 3️⃣ Xem Danh Sách Khóa Học

```bash
# Không cần token (public)
curl -X GET http://localhost:8000/api/courses/
```

**Với filter & search:**
```bash
curl -X GET "http://localhost:8000/api/courses/?search=python&ordering=-id"
```

---

## 4️⃣ Xem Chi Tiết Khóa Học

```bash
curl -X GET http://localhost:8000/api/courses/1/
```

---

## 5️⃣ Đăng Ký Khóa Học

```bash
curl -X POST http://localhost:8000/api/courses/1/enroll/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

---

## 6️⃣ Xem Danh Sách Bài Học

```bash
curl -X GET http://localhost:8000/api/courses/1/lessons/
```

---

## 7️⃣ Xem Danh Sách Quiz

```bash
curl -X GET http://localhost:8000/api/courses/1/quizzes/
```

---

## 8️⃣ Bắt Đầu Bài Quiz

```bash
curl -X POST http://localhost:8000/api/quizzes/1/start/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

**Response:**
```json
{
    "id": 1,
    "user": {...},
    "quiz": {...},
    "started_at": "2024-01-01T10:00:00Z",
    "finished_at": null,
    "score": 0,
    "total_points": 0,
    "completed": false,
    "answers": []
}
```

Lưu giữ `id` (attempt_id) để submit đáp án.

---

## 9️⃣ Submit Đáp Án

```bash
curl -X PUT http://localhost:8000/api/attempts/1/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
        {"question_id": 1, "choice_id": 2},
        {"question_id": 2, "choice_id": 5},
        {"question_id": 3, "choice_id": 8}
    ]
  }'
```

**Response:**
```json
{
    "id": 1,
    "user": {...},
    "quiz": {...},
    "score": 3,
    "total_points": 3,
    "percentage": 100.0,
    "completed": true,
    "answers": [...]
}
```

---

## 🔟 Xem Kết Quả

```bash
curl -X GET http://localhost:8000/api/attempts/1/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

---

## 📋 Các Endpoint Công Khai (Không cần token)

| Method | Endpoint | Mô Tả |
|--------|----------|--------|
| GET | `/courses/` | Danh sách khóa học |
| GET | `/courses/{id}/` | Chi tiết khóa học |
| POST | `/auth/register/` | Đăng ký tài khoản |
| POST | `/auth/login/` | Đăng nhập |

---

## 🔒 Các Endpoint Cần Token

| Method | Endpoint | Mô Tả |
|--------|----------|--------|
| GET | `/auth/user/` | Thông tin user |
| POST | `/auth/logout/` | Đăng xuất |
| GET | `/enrollments/` | Danh sách đăng ký |
| POST | `/courses/{id}/enroll/` | Đăng ký khóa học |
| GET | `/courses/{id}/lessons/` | Danh sách bài học |
| GET | `/courses/{id}/quizzes/` | Danh sách quiz |
| POST | `/quizzes/{id}/start/` | Bắt đầu quiz |
| PUT | `/attempts/{id}/` | Submit đáp án |
| GET | `/my-attempts/` | Danh sách lần làm quiz |

---

## 👨‍🏫 Endpoint Cho Giáo Viên

```bash
# Xem khóa học của mình (bao gồm chưa xuất bản)
curl -X GET http://localhost:8000/api/my-courses/ \
  -H "Authorization: Token YOUR_TOKEN"

# Xem danh sách học viên
curl -X GET http://localhost:8000/api/teacher/enrollments/ \
  -H "Authorization: Token YOUR_TOKEN"

# Xem kết quả quiz học viên
curl -X GET http://localhost:8000/api/teacher/quiz-results/ \
  -H "Authorization: Token YOUR_TOKEN"

# Tạo khóa học mới
curl -X POST http://localhost:8000/api/courses/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Advanced",
    "description": "Advanced Python course",
    "price": 500000,
    "is_free": false,
    "subject": 1,
    "grade": 1,
    "level": 1,
    "is_published": true
  }'
```

---

## 🛠️ Postman Collection

```
Base URL: http://localhost:8000/api/

Variables:
- token: (Lấy từ login response)
- course_id: (Lấy từ courses list)
- quiz_id: (Lấy từ quizzes list)
- attempt_id: (Lấy từ start quiz response)

Headers mặc định:
- Authorization: Bearer {{token}}
- Content-Type: application/json
```

---

## 📱 Python Example

```python
import requests
import json

BASE_URL = "http://localhost:8000/api"
TOKEN = None

# 1. Đăng ký
response = requests.post(f"{BASE_URL}/auth/register/", json={
    "username": "student1",
    "email": "student1@example.com",
    "password": "password123",
    "role": "student"
})
TOKEN = response.json()['token']
print(f"Token: {TOKEN}")

# 2. Xem khóa học
headers = {"Authorization": f"Token {TOKEN}"}
response = requests.get(f"{BASE_URL}/courses/", headers=headers)
courses = response.json()['results']
print(f"Found {len(courses)} courses")

# 3. Đăng ký khóa học đầu tiên
course_id = courses[0]['id']
response = requests.post(f"{BASE_URL}/courses/{course_id}/enroll/", headers=headers)
enrollment = response.json()
print(f"Enrolled to course {course_id}")

# 4. Bắt đầu quiz
quiz_id = courses[0]['quizzes'][0]['id']
response = requests.post(f"{BASE_URL}/quizzes/{quiz_id}/start/", headers=headers)
attempt = response.json()
attempt_id = attempt['id']
print(f"Started attempt {attempt_id}")

# 5. Submit đáp án
answers = []
for question in attempt['quiz']['questions']:
    answers.append({
        "question_id": question['id'],
        "choice_id": question['choices'][0]['id']  # Chọn đáp án đầu
    })

response = requests.put(
    f"{BASE_URL}/attempts/{attempt_id}/",
    headers=headers,
    json={"answers": answers}
)
result = response.json()
print(f"Score: {result['percentage']}%")
```

---

## 🧪 JavaScript/Fetch Example

```javascript
const BASE_URL = 'http://localhost:8000/api';
let token = null;

// 1. Đăng ký
async function register() {
    const response = await fetch(`${BASE_URL}/auth/register/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            username: 'student1',
            email: 'student1@example.com',
            password: 'password123',
            role: 'student'
        })
    });
    const data = await response.json();
    token = data.token;
    console.log('Token:', token);
}

// 2. Xem khóa học
async function getCourses() {
    const response = await fetch(`${BASE_URL}/courses/`);
    const data = await response.json();
    console.log('Courses:', data.results);
    return data.results;
}

// 3. Đăng ký khóa học
async function enrollCourse(courseId) {
    const response = await fetch(`${BASE_URL}/courses/${courseId}/enroll/`, {
        method: 'POST',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        }
    });
    const data = await response.json();
    console.log('Enrolled:', data);
}

// 4. Bắt đầu quiz
async function startQuiz(quizId) {
    const response = await fetch(`${BASE_URL}/quizzes/${quizId}/start/`, {
        method: 'POST',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        }
    });
    const data = await response.json();
    console.log('Attempt:', data);
    return data;
}

// 5. Submit đáp án
async function submitAnswers(attemptId, answers) {
    const response = await fetch(`${BASE_URL}/attempts/${attemptId}/`, {
        method: 'PUT',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({answers: answers})
    });
    const data = await response.json();
    console.log('Result:', data);
    return data;
}

// Chạy
async function main() {
    await register();
    const courses = await getCourses();
    if (courses.length > 0) {
        await enrollCourse(courses[0].id);
        const attempt = await startQuiz(courses[0].quizzes[0].id);
        const answers = attempt.quiz.questions.map(q => ({
            question_id: q.id,
            choice_id: q.choices[0].id
        }));
        await submitAnswers(attempt.id, answers);
    }
}

main();
```

---

## 📖 Xem Chi Tiết

Vào: `API_DOCUMENTATION.md`

---

**Status:** ✅ Ready for Production
