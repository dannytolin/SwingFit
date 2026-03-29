from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class SwingSession(Base):
    __tablename__ = "swing_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    session_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    launch_monitor_type: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)

    trackman_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    trackman_facility_name: Mapped[str | None] = mapped_column(String, nullable=True)
    trackman_bay_id: Mapped[str | None] = mapped_column(String, nullable=True)

    data_source: Mapped[str] = mapped_column(String, nullable=False)

    source_file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source_file_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="sessions")
    shots = relationship("Shot", back_populates="session", order_by="Shot.shot_number")
