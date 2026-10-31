"""Create local student and approver logins without storing passwords in Git.

Run once from the project root after installing Python dependencies:
    python scripts/setup_demo_accounts.py

The passwords are read with getpass and only salted PBKDF2 hashes are stored in
an ignored local SQLite database.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database  # noqa: E402


def read_password(label: str) -> str:
    while True:
        try:
            value = input(label)
            confirm = input("Confirm password: ")
        except (EOFError, OSError):
            print("\nHidden password input is unavailable.")
            print("Your password will be visible while typing.")
            value = input(label)
            confirm = input("Confirm password: ")

        if value != confirm:
            print("Passwords did not match. Try again.")
            continue

        if len(value) < 12:
            print("Use at least 12 characters for this local demo password.")
            continue

        return value


def main() -> None:
    database.init_db()
    students = database.list_students()

    if not students:
        raise SystemExit(
            "No sample students found. Check data/sample_students.csv."
        )

    print("AIDTM Student Support Agent - local demo account setup")
    print("These are fictional accounts. Do not reuse your personal passwords.")
    print(
        "Student usernames:",
        ", ".join(str(s["student_id"]).lower() for s in students),
    )

    student_password = read_password(
        "Set a shared local password for the sample student accounts: "
    )

    approver_password = read_password(
        "Set a separate local password for the approver account: "
    )

    for student in students:
        database.create_or_update_auth_user(
            username=str(student["student_id"]).lower(),
            password=student_password,
            role="student",
            student_id=student["student_id"],
            display_name=student["display_name"],
        )

    database.create_or_update_auth_user(
        username="approver",
        password=approver_password,
        role="approver",
        display_name="Local Demo Approver",
    )

    print("\nLocal accounts created successfully.")
    print(
        "Students:",
        ", ".join(str(s["student_id"]).lower() for s in students),
    )
    print("Approver: approver")
    print("Passwords were not printed.")
    print("Keep the local SQLite database out of GitHub.")


if __name__ == "__main__":
    main()
