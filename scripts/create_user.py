"""Create a user and generate an API key.

Usage:
    python scripts/create_user.py --name "Acme" --email "acme@co.com" --plan starter
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import SessionLocal  # noqa: E402
from app.models.tables import ApiKey, Plan, User  # noqa: E402
from app.utils.security import generate_api_key  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a user and an API key")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--plan", default="starter")
    parser.add_argument("--label", default="Primary key")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.name == args.plan).one_or_none()
        if plan is None:
            print(f"Error: plan '{args.plan}' does not exist. Run create_plan.py --seed first.",
                  file=sys.stderr)
            return 1

        existing = db.query(User).filter(User.email == args.email).one_or_none()
        if existing is not None:
            print(f"Error: user with email {args.email} already exists.", file=sys.stderr)
            return 1

        user = User(name=args.name, email=args.email, plan_id=plan.id)
        db.add(user)
        db.flush()

        raw_key, key_hash, key_prefix = generate_api_key()
        api_key = ApiKey(
            user_id=user.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            label=args.label,
        )
        db.add(api_key)
        db.commit()

        print("User created successfully.")
        print(f"  Name:  {user.name}")
        print(f"  Email: {user.email}")
        print(f"  Plan:  {plan.name}")
        print()
        print("API KEY (shown ONCE — store it securely, it cannot be retrieved again):")
        print(f"  {raw_key}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
