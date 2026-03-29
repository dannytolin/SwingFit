import re

_WEDGE_ABBREVS = {"pw", "gw", "sw", "lw", "aw"}
_WOOD_RE = re.compile(r"^(\d)\s*[-]?\s*(?:wood|w)$", re.IGNORECASE)
_HYBRID_RE = re.compile(r"^(\d)\s*[-]?\s*(?:hybrid|h)$", re.IGNORECASE)
_IRON_RE = re.compile(r"^(\d)\s*[-]?\s*(?:iron|i)$", re.IGNORECASE)
_DEGREE_RE = re.compile(r"^(\d{2})\s*[°]?\s*(?:degree)?$", re.IGNORECASE)


def normalize_club_name(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.lower() == "driver":
        return "driver"
    if cleaned.lower() == "putter":
        return "putter"
    if cleaned.lower() in _WEDGE_ABBREVS:
        return cleaned.upper()
    m = _WOOD_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-wood"
    m = _HYBRID_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-hybrid"
    m = _IRON_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-iron"
    m = _DEGREE_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-degree"
    return re.sub(r"\s+", "-", cleaned.lower())
