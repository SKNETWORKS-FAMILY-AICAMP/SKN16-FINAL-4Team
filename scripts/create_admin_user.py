#!/usr/bin/env python3
"""Create an admin user in the project's database.

This script uses the project's `database.py`, `models.py` and `hashing.py`.
It will require a unique `email` (schema requires non-null unique email).

Example:
  python3 scripts/create_admin_user.py --email admin@example.com
"""
import sys
import getpass
from sqlalchemy import or_

from database import SessionLocal
from models import User
from hashing import hash_password


def prompt_nonempty(prompt_text: str) -> str:
    while True:
        try:
            v = input(prompt_text).strip()
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(1)
        if v:
            return v
        print("입력값은 비어있을 수 없습니다. 다시 시도하세요.")


def main():
    print("관리자 계정 생성 — 모든 항목을 입력해주세요.")
    username = prompt_nonempty("Username: ")
    nickname = prompt_nonempty("Nickname: ")
    email = prompt_nonempty("Email: ")

    while True:
        try:
            password_plain = getpass.getpass("Password: ")
            password_confirm = getpass.getpass("Confirm Password: ")
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(1)
        if not password_plain:
            print("비밀번호는 비어있을 수 없습니다. 다시 입력하세요.")
            continue
        if password_plain != password_confirm:
            print("비밀번호가 일치하지 않습니다. 다시 입력하세요.")
            continue
        break

    hashed = hash_password(password_plain)

    db = SessionLocal()
    try:
        # Check for conflicts with username, nickname or email
        existing = db.query(User).filter(
            or_(User.username == username, User.nickname == nickname, User.email == email)
        ).first()
        if existing:
            print("동일한 username, nickname 또는 email을 가진 사용자가 이미 존재합니다:")
            print(f"  id={existing.id}, username={existing.username}, nickname={existing.nickname}, email={existing.email}")
            print("변경하지 않았습니다.")
            return

        user = User(
            username=username,
            nickname=nickname,
            password=hashed,
            email=email,
            role="admin",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"관리자 계정이 생성되었습니다. id={user.id}, username={user.username}, nickname={user.nickname}, email={user.email}")
    except Exception as e:
        db.rollback()
        print("관리자 생성 중 오류가 발생했습니다:", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
