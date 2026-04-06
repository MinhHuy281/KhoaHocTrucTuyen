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

    status_code, courses_payload = scoped_request("GET", "/courses/")
    if isinstance(courses_payload, dict) and courses_payload.get("error") in {"connection_error", "timeout"}:
        return 1
    print(f"[GET] /courses/ -> {status_code}")
    print(pretty(courses_payload))

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
    print(f"[POST] /auth/register/ -> {register_status}")
    print(pretty(register_payload))

    login_status, login_payload = scoped_login_user(args.username, args.password)
    print(f"[POST] /auth/login/ -> {login_status}")
    print(pretty(login_payload))

    token = login_payload.get("token") if isinstance(login_payload, dict) else None
    if not token:
        print("Không lấy được token. Dừng script.")
        return 1

    user_status, user_payload = scoped_request("GET", "/auth/user/", token=token)
    print(f"[GET] /auth/user/ -> {user_status}")
    print(pretty(user_payload))

    if chosen_course and chosen_course.get("id"):
        course_id = chosen_course["id"]
        enroll_status, enroll_payload = scoped_request("POST", f"/courses/{course_id}/enroll/", token=token)
        print(f"[POST] /courses/{course_id}/enroll/ -> {enroll_status}")
        print(pretty(enroll_payload))

        quiz_status, quiz_payload = scoped_request("GET", f"/courses/{course_id}/quizzes/", token=token)
        print(f"[GET] /courses/{course_id}/quizzes/ -> {quiz_status}")
        print(pretty(quiz_payload))

        quizzes = extract_results(quiz_payload)
        chosen_quiz_id = args.quiz_id or (quizzes[0]["id"] if quizzes else None)

        if chosen_quiz_id:
            start_status, start_payload = scoped_request("POST", f"/quizzes/{chosen_quiz_id}/start/", token=token)
            print(f"[POST] /quizzes/{chosen_quiz_id}/start/ -> {start_status}")
            print(pretty(start_payload))

            if isinstance(start_payload, dict) and start_status in (200, 201):
                attempt_id = start_payload.get("id")
                if attempt_id:
                    attempt_status, attempt_payload = scoped_request("GET", f"/attempts/{attempt_id}/", token=token)
                    print(f"[GET] /attempts/{attempt_id}/ -> {attempt_status}")
                    print(pretty(attempt_payload))
        else:
            print("Không có quiz nào để test start quiz.")
    else:
        print("Không có course nào để test enroll/quiz.")

    print("=" * 60)
    print("API smoke test completed")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())