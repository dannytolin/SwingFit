import csv
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.club_spec import ClubSpec


def seed_clubs_from_csv(db: Session, csv_path: str) -> int:
    """Load club specs from CSV into database. Returns count of new records."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {csv_path}")

    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing = db.query(ClubSpec).filter(
                ClubSpec.brand == row["brand"],
                ClubSpec.model_name == row["model_name"],
                ClubSpec.model_year == int(row["model_year"]),
                ClubSpec.club_type == row["club_type"],
            ).first()
            if existing:
                continue

            club = ClubSpec(
                brand=row["brand"],
                model_name=row["model_name"],
                model_year=int(row["model_year"]),
                club_type=row["club_type"],
                loft=_float_or_none(row.get("loft")),
                lie_angle=_float_or_none(row.get("lie_angle")),
                shaft_options=row.get("shaft_options") or None,
                head_weight=_float_or_none(row.get("head_weight")),
                adjustable=row.get("adjustable", "").strip().lower() == "true",
                loft_range_min=_float_or_none(row.get("loft_range_min")),
                loft_range_max=_float_or_none(row.get("loft_range_max")),
                launch_bias=row.get("launch_bias") or None,
                spin_bias=row.get("spin_bias") or None,
                forgiveness_rating=_int_or_none(row.get("forgiveness_rating")),
                workability_rating=_int_or_none(row.get("workability_rating")),
                swing_speed_min=_float_or_none(row.get("swing_speed_min")),
                swing_speed_max=_float_or_none(row.get("swing_speed_max")),
                msrp=_float_or_none(row.get("msrp")),
                avg_used_price=_float_or_none(row.get("avg_used_price")),
                still_in_production=row.get("still_in_production", "").strip().lower() == "true",
            )
            db.add(club)
            count += 1
    db.commit()
    return count


def _float_or_none(val: str | None) -> float | None:
    if not val or val.strip() == "":
        return None
    return float(val)


def _int_or_none(val: str | None) -> int | None:
    if not val or val.strip() == "":
        return None
    return int(val)


if __name__ == "__main__":
    from backend.app.database import SessionLocal, engine, Base
    from backend.app.models import ClubSpec as _ClubSpec  # noqa: F811

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        count = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
        print(f"Seeded {count} club specs")
    finally:
        db.close()
