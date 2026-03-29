from datetime import datetime

from pydantic import BaseModel


class SwingSessionCreate(BaseModel):
    session_date: datetime | None = None
    launch_monitor_type: str
    location: str | None = None
    trackman_session_id: str | None = None
    trackman_facility_name: str | None = None
    trackman_bay_id: str | None = None
    data_source: str
    source_file_name: str | None = None
    source_file_hash: str | None = None


class SwingSessionRead(SwingSessionCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
