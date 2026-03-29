from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CLUB_TYPES = Literal["driver", "iron", "hybrid", "fairway", "wedge", "putter"]
BIAS_OPTIONS = Literal["low", "mid", "high"]


class ClubSpecCreate(BaseModel):
    brand: str
    model_name: str
    model_year: int
    club_type: CLUB_TYPES
    loft: float | None = None
    lie_angle: float | None = None
    shaft_options: str | None = None
    head_weight: float | None = None
    adjustable: bool = False
    loft_range_min: float | None = None
    loft_range_max: float | None = None
    launch_bias: BIAS_OPTIONS | None = None
    spin_bias: BIAS_OPTIONS | None = None
    forgiveness_rating: int | None = Field(None, ge=1, le=10)
    workability_rating: int | None = Field(None, ge=1, le=10)
    swing_speed_min: float | None = None
    swing_speed_max: float | None = None
    msrp: float | None = None
    avg_used_price: float | None = None
    affiliate_url_template: str | None = None
    still_in_production: bool = True


class ClubSpecRead(ClubSpecCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClubSpecSearch(BaseModel):
    brand: str | None = None
    club_type: CLUB_TYPES | None = None
    model_year: int | None = None
    swing_speed: float | None = None
    launch_bias: BIAS_OPTIONS | None = None
    spin_bias: BIAS_OPTIONS | None = None
