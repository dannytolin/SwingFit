from backend.app.services.data_quality import get_data_quality, DATA_QUALITY_TIERS


def test_trackman_file_is_platinum():
    dq = get_data_quality("trackman_4", "file_upload")
    assert dq["tier"] == "platinum"
    assert dq["weight"] == 1.0
    assert dq["has_club_data"] is True


def test_trackman_ocr_is_silver():
    dq = get_data_quality("trackman_4", "ocr_vision")
    assert dq["tier"] == "silver"
    assert dq["weight"] == 0.7


def test_garmin_r10_is_silver():
    dq = get_data_quality("garmin_r10", "file_upload")
    assert dq["tier"] == "silver"
    assert dq["weight"] == 0.7


def test_manual_entry_is_bronze():
    dq = get_data_quality("manual", "manual_entry")
    assert dq["tier"] == "bronze"
    assert dq["weight"] == 0.3


def test_unknown_source_is_bronze():
    dq = get_data_quality("unknown_monitor", "file_upload")
    assert dq["tier"] == "bronze"
    assert dq["weight"] == 0.5


def test_all_tiers_have_required_keys():
    for key, tier in DATA_QUALITY_TIERS.items():
        assert "tier" in tier
        assert "weight" in tier
        assert "has_club_data" in tier
        assert "has_spin_axis" in tier
