"""Seed the filaments table with common materials.

Usage:
    python scripts/seed_filaments.py
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import SessionLocal  # noqa: E402
from app.models.tables import Filament  # noqa: E402


FILAMENTS = [
    {"type": "PLA",   "display_name": "PLA Basic",        "density_g_per_cm3": Decimal("1.2400"), "cost_per_kg": Decimal("20.00")},
    {"type": "ABS",   "display_name": "ABS Standard",     "density_g_per_cm3": Decimal("1.0400"), "cost_per_kg": Decimal("22.00")},
    {"type": "PETG",  "display_name": "PETG Standard",    "density_g_per_cm3": Decimal("1.2700"), "cost_per_kg": Decimal("25.00")},
    {"type": "TPU",   "display_name": "TPU Flexible",     "density_g_per_cm3": Decimal("1.2100"), "cost_per_kg": Decimal("35.00")},
    {"type": "Nylon", "display_name": "Nylon PA12",       "density_g_per_cm3": Decimal("1.1400"), "cost_per_kg": Decimal("40.00")},
    {"type": "ASA",   "display_name": "ASA UV-Resistant", "density_g_per_cm3": Decimal("1.0700"), "cost_per_kg": Decimal("28.00")},
    {"type": "PC",    "display_name": "Polycarbonate",    "density_g_per_cm3": Decimal("1.2000"), "cost_per_kg": Decimal("45.00")},
    {"type": "PVA",   "display_name": "PVA Soluble",      "density_g_per_cm3": Decimal("1.2300"), "cost_per_kg": Decimal("50.00")},
]


def main() -> int:
    db = SessionLocal()
    try:
        for data in FILAMENTS:
            existing = db.query(Filament).filter(Filament.type == data["type"]).one_or_none()
            if existing is None:
                db.add(Filament(**data))
            else:
                existing.display_name = data["display_name"]
                existing.density_g_per_cm3 = data["density_g_per_cm3"]
                existing.cost_per_kg = data["cost_per_kg"]
        db.commit()
        print(f"Seeded {len(FILAMENTS)} filaments.")
        for f in FILAMENTS:
            print(f"  - {f['type']}: ${f['cost_per_kg']}/kg @ {f['density_g_per_cm3']} g/cm3")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
