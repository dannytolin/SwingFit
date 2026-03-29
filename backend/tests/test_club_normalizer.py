from backend.app.utils.club_normalizer import normalize_club_name


def test_driver():
    assert normalize_club_name("Driver") == "driver"
    assert normalize_club_name("DRIVER") == "driver"
    assert normalize_club_name("driver") == "driver"


def test_fairway_woods():
    assert normalize_club_name("3 Wood") == "3-wood"
    assert normalize_club_name("3-Wood") == "3-wood"
    assert normalize_club_name("3W") == "3-wood"
    assert normalize_club_name("5 Wood") == "5-wood"
    assert normalize_club_name("7 Wood") == "7-wood"


def test_hybrids():
    assert normalize_club_name("4 Hybrid") == "4-hybrid"
    assert normalize_club_name("3 Hybrid") == "3-hybrid"
    assert normalize_club_name("3H") == "3-hybrid"
    assert normalize_club_name("5 Hybrid") == "5-hybrid"


def test_irons():
    assert normalize_club_name("5 Iron") == "5-iron"
    assert normalize_club_name("7 Iron") == "7-iron"
    assert normalize_club_name("7I") == "7-iron"
    assert normalize_club_name("7-iron") == "7-iron"
    assert normalize_club_name("9 Iron") == "9-iron"


def test_wedges():
    assert normalize_club_name("PW") == "PW"
    assert normalize_club_name("pw") == "PW"
    assert normalize_club_name("GW") == "GW"
    assert normalize_club_name("SW") == "SW"
    assert normalize_club_name("LW") == "LW"
    assert normalize_club_name("56°") == "56-degree"
    assert normalize_club_name("60 Degree") == "60-degree"


def test_putter():
    assert normalize_club_name("Putter") == "putter"


def test_unknown_passthrough():
    assert normalize_club_name("Custom Club") == "custom-club"
