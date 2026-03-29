from pydantic import BaseModel


class ShotCreate(BaseModel):
    club_used: str
    club_brand: str | None = None
    club_model: str | None = None
    ball_speed: float
    launch_angle: float
    spin_rate: float
    spin_axis: float | None = None
    carry_distance: float
    total_distance: float | None = None
    club_speed: float | None = None
    smash_factor: float | None = None
    attack_angle: float | None = None
    club_path: float | None = None
    face_angle: float | None = None
    face_to_path: float | None = None
    offline_distance: float | None = None
    apex_height: float | None = None
    landing_angle: float | None = None
    dynamic_loft: float | None = None
    spin_loft: float | None = None
    hang_time: float | None = None
    last_data_distance: float | None = None
    is_valid: bool = True
    shot_number: int


class ShotRead(ShotCreate):
    id: int
    session_id: int

    model_config = {"from_attributes": True}
