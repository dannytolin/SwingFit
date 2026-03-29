DATA_QUALITY_TIERS: dict[str, dict] = {
    "trackman_4_file": {"tier": "platinum", "weight": 1.0, "has_club_data": True, "has_spin_axis": True},
    "trackman_4_bridge": {"tier": "platinum", "weight": 1.0, "has_club_data": True, "has_spin_axis": True},
    "trackman_range_api": {"tier": "gold", "weight": 0.85, "has_club_data": False, "has_spin_axis": False},
    "trackman_report_ocr": {"tier": "silver", "weight": 0.7, "has_club_data": True, "has_spin_axis": True},
    "garmin_r10": {"tier": "silver", "weight": 0.7, "has_club_data": True, "has_spin_axis": False},
    "rapsodo_mlm2": {"tier": "silver", "weight": 0.7, "has_club_data": True, "has_spin_axis": False},
    "fullswing_kit": {"tier": "silver", "weight": 0.7, "has_club_data": True, "has_spin_axis": True},
    "generic_csv": {"tier": "bronze", "weight": 0.5, "has_club_data": False, "has_spin_axis": False},
    "manual_entry": {"tier": "bronze", "weight": 0.3, "has_club_data": False, "has_spin_axis": False},
}

_LOOKUP: dict[tuple[str, str], str] = {
    ("trackman_4", "file_upload"): "trackman_4_file",
    ("trackman_4", "bridge"): "trackman_4_bridge",
    ("trackman_range", "api_realtime"): "trackman_range_api",
    ("trackman_4", "ocr_vision"): "trackman_report_ocr",
    ("garmin_r10", "file_upload"): "garmin_r10",
    ("rapsodo_mlm2", "file_upload"): "rapsodo_mlm2",
    ("fullswing_kit", "file_upload"): "fullswing_kit",
    ("manual", "manual_entry"): "manual_entry",
}

_DEFAULT_TIER = DATA_QUALITY_TIERS["generic_csv"]


def get_data_quality(launch_monitor_type: str, data_source: str) -> dict:
    key = (launch_monitor_type, data_source)
    tier_key = _LOOKUP.get(key)
    if tier_key:
        return DATA_QUALITY_TIERS[tier_key]
    return _DEFAULT_TIER
