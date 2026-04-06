from __future__ import annotations

import os

import pymysql


DB_CONFIG = {
	"host": os.getenv("DB_HOST", "127.0.0.1"),
	"user": os.getenv("DB_USER", "root"),
	"password": os.getenv("DB_PASSWORD", "1234"),
	"database": os.getenv("DB_NAME", "khoahoctructuyen"),
	"charset": "utf8mb4",
	"autocommit": True,
}


def main() -> None:
	connection = pymysql.connect(**DB_CONFIG)
	try:
		with connection.cursor() as cursor:
			cursor.execute(
				"""
				SELECT CONSTRAINT_NAME
				FROM information_schema.REFERENTIAL_CONSTRAINTS
				WHERE CONSTRAINT_SCHEMA = %s
				  AND TABLE_NAME = 'courses_payment'
				""",
				(DB_CONFIG["database"],),
			)
			existing_constraints = [row[0] for row in cursor.fetchall()]

			for constraint_name in existing_constraints:
				cursor.execute(f"ALTER TABLE courses_payment DROP FOREIGN KEY {constraint_name}")
				print(f"OK: dropped {constraint_name}")

			cursor.execute(
				"""
				DELETE FROM courses_payment
				WHERE course_id NOT IN (SELECT id FROM courses_course)
				   OR enrollment_id IS NOT NULL AND enrollment_id NOT IN (SELECT id FROM courses_enrollment)
				   OR user_id NOT IN (SELECT id FROM auth_user)
				"""
			)
			print(f"OK: deleted orphan payment rows ({cursor.rowcount})")

			add_statements = [
				"ALTER TABLE courses_payment ADD CONSTRAINT courses_payment_course_id_b5b54a0d_fk_courses_course_id FOREIGN KEY (course_id) REFERENCES courses_course (id) ON DELETE CASCADE ON UPDATE CASCADE",
				"ALTER TABLE courses_payment ADD CONSTRAINT courses_payment_enrollment_id_a4d02d64_fk_courses_enrollment_id FOREIGN KEY (enrollment_id) REFERENCES courses_enrollment (id) ON DELETE CASCADE ON UPDATE CASCADE",
				"ALTER TABLE courses_payment ADD CONSTRAINT courses_payment_user_id_4aaeee29_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE ON UPDATE CASCADE",
			]

			for statement in add_statements:
				cursor.execute(statement)
				print(f"OK: {statement}")

		print("\nĐã sửa xong foreign key của courses_payment.")
		print("Bây giờ xóa user sẽ không còn bị chặn bởi bảng payment.")
	finally:
		connection.close()


if __name__ == "__main__":
	main()
