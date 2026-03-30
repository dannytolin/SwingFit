from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    club_type: Mapped[str] = mapped_column(String, nullable=False)
    club_spec_id: Mapped[int] = mapped_column(Integer, nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    projected_changes: Mapped[str | None] = mapped_column(Text, nullable=True)
    best_for: Mapped[str | None] = mapped_column(String, nullable=True)
    recommended_build: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
