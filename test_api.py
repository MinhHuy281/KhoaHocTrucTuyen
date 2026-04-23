from __future__ import annotations

import argparse
import json
import time
from typing import Any, Optional

import requests
from requests import exceptions as requests_exceptions


BASE_URL = "http://127.0.0.1:8000/api"
TIMEOUT = 15


def pretty(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def extract_results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    if isinstance(payload, list):
        return payload
    return []


def request_json(method: str, path: str, *, token: Optional[str] = None, payload: Optional[dict[str, Any]] = None) -> tuple[int, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"

    response = requests.request(
        method=method,
        url=f"{BASE_URL}{path}",
        headers=headers,
        json=payload,
        timeout=TIMEOUT,
    )

    try:
        data = response.json()
    except ValueError:
        data = response.text
    return response.status_code, data


def register_user(username: str, password: str, role: str = "student") -> tuple[int, Any]:
    return request_json(
        "POST",
        "/auth/register/",
        payload={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )


def login_user(username: str, password: str) -> tuple[int, Any]:
    return request_json(
        "POST",
        "/auth/login/",
        payload={"username": username, "password": password},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test cho API KhoaHocTrucTuyen")
    parser.add_argument("--base-url", default=BASE_URL, help="Base URL của API")
    parser.add_argument("--username", default=f"testuser_{int(time.time())}", help="Username test")
    parser.add_argument("--password", default="Test@123456", help="Password test")
    parser.add_argument("--role", default="student", choices=["student", "teacher"], help="Role test")
    parser.add_argument("--course-id", type=int, default=None, help="Course ID cụ thể nếu muốn test enroll")
    parser.add_argument("--quiz-id", type=int, default=None, help="Quiz ID cụ thể nếu muốn test start quiz")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    print("=" * 60)
    print("TESTING KHOAHOCTRUCTUYEN API")
    print(f"Base URL: {base_url}")
    print("=" * 60)

    def scoped_request(method: str, path: str, *, token: Optional[str] = None, payload: Optional[dict[str, Any]] = None) -> tuple[int, Any]:
        nonlocal base_url
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Token {token}"

        try:
            response = requests.request(
                method=method,
                url=f"{base_url}{path}",
                headers=headers,
                json=payload,
                timeout=TIMEOUT,
            )
        except requests_exceptions.ConnectionError:
            print()
            print("Không thể kết nối tới API server.")
            print(f"Hãy kiểm tra server đang chạy tại: {base_url}")
            print("Lệnh gợi ý: python manage.py runserver")
            return 0, {"error": "connection_error", "detail": "API server is not running"}
        except requests_exceptions.Timeout:
            print()
            print("API server phản hồi quá lâu (timeout).")
            print(f"Hãy kiểm tra server tại: {base_url}")
            return 0, {"error": "timeout", "detail": "API request timed out"}

        try:
            data = response.json()
        except ValueError:
            data = response.text
        return response.status_code, data

    checks: list[tuple[str, int, bool]] = []

    def record_check(name: str, status_code: int, ok_codes: set[int]) -> None:
        checks.append((name, status_code, status_code in ok_codes))

    status_code, courses_payload = scoped_request("GET", "/courses/")
    if isinstance(courses_payload, dict) and courses_payload.get("error") in {"connection_error", "timeout"}:
        return 1
    record_check("GET /courses/", status_code, {200})
    print(f"[GET] /courses/ -> {status_code}")
    print(pretty(courses_payload))

    levels_status, levels_payload = scoped_request("GET", "/levels/")
    record_check("GET /levels/", levels_status, {200})
    print(f"[GET] /levels/ -> {levels_status}")
    print(pretty(levels_payload))

    grades_status, grades_payload = scoped_request("GET", "/grades/")
    record_check("GET /grades/", grades_status, {200})
    print(f"[GET] /grades/ -> {grades_status}")
    print(pretty(grades_payload))

    subjects_status, subjects_payload = scoped_request("GET", "/subjects/")
    record_check("GET /subjects/", subjects_status, {200})
    print(f"[GET] /subjects/ -> {subjects_status}")
    print(pretty(subjects_payload))

    courses = extract_results(courses_payload)
    chosen_course = {"id": args.course_id} if args.course_id is not None else (courses[0] if courses else None)

    def scoped_register_user(username: str, password: str, role: str = "student") -> tuple[int, Any]:
        return scoped_request(
            "POST",
            "/auth/register/",
            payload={
                "username": username,
                "email": f"{username}@example.com",
                "password": password,
                "first_name": "Test",
                "last_name": "User",
                "role": role,
            },
        )

    def scoped_login_user(username: str, password: str) -> tuple[int, Any]:
        return scoped_request(
            "POST",
            "/auth/login/",
            payload={"username": username, "password": password},
        )

    register_status, register_payload = scoped_register_user(args.username, args.password, args.role)
    record_check("POST /auth/register/", register_status, {201})
    print(f"[POST] /auth/register/ -> {register_status}")
    print(pretty(register_payload))

    login_status, login_payload = scoped_login_user(args.username, args.password)
    record_check("POST /auth/login/", login_status, {200})
    print(f"[POST] /auth/login/ -> {login_status}")
    print(pretty(login_payload))

    token = login_payload.get("token") if isinstance(login_payload, dict) else None
    if not token:
        print("Không lấy được token. Dừng script.")
        return 1

    user_status, user_payload = scoped_request("GET", "/auth/user/", token=token)
    record_check("GET /auth/user/", user_status, {200})
    print(f"[GET] /auth/user/ -> {user_status}")
    print(pretty(user_payload))

    enrollments_status, enrollments_payload = scoped_request("GET", "/enrollments/", token=token)
    record_check("GET /enrollments/", enrollments_status, {200})
    print(f"[GET] /enrollments/ -> {enrollments_status}")
    print(pretty(enrollments_payload))

    attempts_status, attempts_payload = scoped_request("GET", "/my-attempts/", token=token)
    record_check("GET /my-attempts/", attempts_status, {200})
    print(f"[GET] /my-attempts/ -> {attempts_status}")
    print(pretty(attempts_payload))

    notifications_status, notifications_payload = scoped_request("GET", "/notifications/", token=token)
    record_check("GET /notifications/", notifications_status, {200})
    print(f"[GET] /notifications/ -> {notifications_status}")
    print(pretty(notifications_payload))

    if args.role == "teacher":
        my_courses_status, my_courses_payload = scoped_request("GET", "/my-courses/", token=token)
        record_check("GET /my-courses/", my_courses_status, {200})
        print(f"[GET] /my-courses/ -> {my_courses_status}")
        print(pretty(my_courses_payload))

        teacher_enrollments_status, teacher_enrollments_payload = scoped_request("GET", "/teacher/enrollments/", token=token)
        record_check("GET /teacher/enrollments/", teacher_enrollments_status, {200})
        print(f"[GET] /teacher/enrollments/ -> {teacher_enrollments_status}")
        print(pretty(teacher_enrollments_payload))

        teacher_quiz_results_status, teacher_quiz_results_payload = scoped_request("GET", "/teacher/quiz-results/", token=token)
        record_check("GET /teacher/quiz-results/", teacher_quiz_results_status, {200})
        print(f"[GET] /teacher/quiz-results/ -> {teacher_quiz_results_status}")
        print(pretty(teacher_quiz_results_payload))

    if chosen_course and chosen_course.get("id"):
        course_id = chosen_course["id"]
        enroll_status, enroll_payload = scoped_request("POST", f"/courses/{course_id}/enroll/", token=token)
        record_check(f"POST /courses/{course_id}/enroll/", enroll_status, {201, 400})
        print(f"[POST] /courses/{course_id}/enroll/ -> {enroll_status}")
        print(pretty(enroll_payload))

        quiz_status, quiz_payload = scoped_request("GET", f"/courses/{course_id}/quizzes/", token=token)
        record_check(f"GET /courses/{course_id}/quizzes/", quiz_status, {200})
        print(f"[GET] /courses/{course_id}/quizzes/ -> {quiz_status}")
        print(pretty(quiz_payload))

        quizzes = extract_results(quiz_payload)
        chosen_quiz_id = args.quiz_id or (quizzes[0]["id"] if quizzes else None)

        if chosen_quiz_id:
            start_status, start_payload = scoped_request("POST", f"/quizzes/{chosen_quiz_id}/start/", token=token)
            record_check(f"POST /quizzes/{chosen_quiz_id}/start/", start_status, {201, 400, 403})
            print(f"[POST] /quizzes/{chosen_quiz_id}/start/ -> {start_status}")
            print(pretty(start_payload))

            if isinstance(start_payload, dict) and start_status in (200, 201):
                attempt_id = start_payload.get("id")
                if attempt_id:
                    attempt_status, attempt_payload = scoped_request("GET", f"/attempts/{attempt_id}/", token=token)
                    record_check(f"GET /attempts/{attempt_id}/", attempt_status, {200})
                    print(f"[GET] /attempts/{attempt_id}/ -> {attempt_status}")
                    print(pretty(attempt_payload))
        else:
            print("Không có quiz nào để test start quiz.")
    else:
        print("Không có course nào để test enroll/quiz.")

    logout_status, logout_payload = scoped_request("POST", "/auth/logout/", token=token)
    record_check("POST /auth/logout/", logout_status, {200})
    print(f"[POST] /auth/logout/ -> {logout_status}")
    print(pretty(logout_payload))

    print("=" * 60)
    print("API smoke test completed")
    print("=" * 60)

    failed = [check for check in checks if not check[2]]
    print("CHECK SUMMARY")
    for name, status_code, passed in checks:
        state = "PASS" if passed else "FAIL"
        print(f"- [{state}] {name} -> {status_code}")

    if failed:
        print("=" * 60)
        print(f"Total failed checks: {len(failed)}")
        return 1

    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())