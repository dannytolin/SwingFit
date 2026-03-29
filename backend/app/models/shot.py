from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("swing_sessions.id"), nullable=False)

    club_used: Mapped[str] = mapped_column(String, nullable=False)
    club_brand: Mapped[str | None] = mapped_column(String, nullable=True)
    club_model: Mapped[str | None] = mapped_column(String, nullable=True)

    ball_speed: Mapped[float] = mapped_column(Float, nullable=False)
    launch_angle: Mapped[float] = mapped_column(Float, nullable=False)
    spin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    spin_axis: Mapped[float | None] = mapped_column(Float, nullable=True)
    carry_distance: Mapped[float] = mapped_column(Float, nullable=False)
    total_distance: Mapped[float | None] = mapped_column(Float, nullable=True)

    club_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    smash_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    attack_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    club_path: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_to_path: Mapped[float | None] = mapped_column(Float, nullable=True)

    offline_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    apex_height: Mapped[float | None] = mapped_column(Float, nullable=True)

    landing_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    dynamic_loft: Mapped[float | None] = mapped_column(Float, nullable=True)
    spin_loft: Mapped[float | None] = mapped_column(Float, nullable=True)
    hang_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_data_distance: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False)

    session = relationship("SwingSession", back_populates="shots")
