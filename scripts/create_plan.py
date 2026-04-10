"""Create subscription plans in the database.

Usage:
    python scripts/create_plan.py --seed
    python scripts/create_plan.py --name starter --monthly-price 29 \
        --requests-per-month 500 --max-file-size-mb 25
"""
import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import SessionLocal  # noqa: E402
from app.models.tables import Plan  # noqa: E402


DEFAULT_PLANS = [
    {
        "name": "starter",
        "display_name": "Starter Plan",
        "monthly_price": Decimal("29.00"),
        "requests_per_month": 500,
        "max_file_size_mb": 25,
    },
    {
        "name": "professional",
        "display_name": "Professional Plan",
        "monthly_price": Decimal("99.00"),
        "requests_per_month": 2000,
        "max_file_size_mb": 50,
    },
    {
        "name": "enterprise",
        "display_name": "Enterprise Plan",
        "monthly_price": Decimal("299.00"),
        "requests_per_month": 10000,
        "max_file_size_mb": 100,
    },
]


def upsert_plan(db, data: dict) -> Plan:
    plan = db.query(Plan).filter(Plan.name == data["name"]).one_or_none()
    if plan is None:
        plan = Plan(**data)
        db.add(plan)
    else:
        for key, value in data.items():
            setattr(plan, key, value)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or seed subscription plans")
    parser.add_argument("--seed", action="store_true", help="Create default plan set")
    parser.add_argument("--name")
    parser.add_argument("--display-name")
    parser.add_argument("--monthly-price", type=Decimal)
    parser.add_argument("--requests-per-month", type=int)
    parser.add_argument("--max-file-size-mb", type=int)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.seed:
            for data in DEFAULT_PLANS:
                upsert_plan(db, data)
            db.commit()
            print(f"Seeded {len(DEFAULT_PLANS)} plans.")
            for p in DEFAULT_PLANS:
                print(f"  - {p['name']}: ${p['monthly_price']}/mo, "
                      f"{p['requests_per_month']} req, {p['max_file_size_mb']}MB")
            return 0

        required = [args.name, args.monthly_price, args.requests_per_month, args.max_file_size_mb]
        if any(v is None for v in required):
            parser.error("--name, --monthly-price, --requests-per-month, --max-file-size-mb are required without --seed")

        data = {
            "name": args.name,
            "display_name": args.display_name or args.name.title(),
            "monthly_price": args.monthly_price,
            "requests_per_month": args.requests_per_month,
            "max_file_size_mb": args.max_file_size_mb,
        }
        upsert_plan(db, data)
        db.commit()
        print(f"Plan '{args.name}' created/updated.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
