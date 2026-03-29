from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ClubSpec(Base):
    __tablename__ = "club_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identity
    brand: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_year: Mapped[int] = mapped_column(Integer, nullable=False)
    club_type: Mapped[str] = mapped_column(String, nullable=False)

    # Specifications
    loft: Mapped[float | None] = mapped_column(Float, nullable=True)
    lie_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    shaft_options: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjustable: Mapped[bool] = mapped_column(Boolean, default=False)
    loft_range_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    loft_range_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Performance profile
    launch_bias: Mapped[str | None] = mapped_column(String, nullable=True)
    spin_bias: Mapped[str | None] = mapped_column(String, nullable=True)
    forgiveness_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workability_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Swing speed suitability
    swing_speed_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    swing_speed_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Market data
    msrp: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_used_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    affiliate_url_template: Mapped[str | None] = mapped_column(String, nullable=True)

    # Metadata
    still_in_production: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
