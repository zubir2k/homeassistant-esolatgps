"""Offline GPS -> JAKIM zone lookup against the bundled polygons."""
import pytest

from custom_components.esolatgps.zones import ZoneIndex


@pytest.fixture(scope="module")
def index() -> ZoneIndex:
    return ZoneIndex.load()


@pytest.mark.parametrize(
    ("lat", "lon", "zone"),
    [
        (3.0218853, 101.7915175, "SGR01"),  # Kajang
        (3.1390, 101.6869, "WLY01"),        # Kuala Lumpur
        (5.4164, 100.3327, "PNG01"),        # George Town
        (1.4927, 103.7414, "JHR02"),        # Johor Bahru
        (6.3300, 99.8500, "KDH06"),         # Langkawi
        (5.9804, 116.0735, "SBH07"),        # Kota Kinabalu
        (1.5535, 110.3593, "SWK08"),        # Kuching
        (2.1900, 102.2500, "MLK01"),        # Melaka
    ],
)
def test_known_places(index: ZoneIndex, lat, lon, zone) -> None:
    match = index.lookup(lat, lon)
    assert match is not None and match.zone == zone and match.exact


def test_zone_names_are_bundled(index: ZoneIndex) -> None:
    m = index.lookup(3.0218853, 101.7915175)
    assert m.negeri == "Selangor"
    assert m.daerah.startswith("Gombak")
    assert len(index.zones) == 60


def test_outside_malaysia(index: ZoneIndex) -> None:
    assert index.lookup(1.3521, 103.8198) is None   # central Singapore
    assert index.lookup(13.75, 100.5) is None       # Bangkok
    assert index.lookup(-6.2, 106.8) is None        # Jakarta


def test_just_offshore_is_nearest_zone(index: ZoneIndex) -> None:
    m = index.lookup(1.445, 103.77)  # Johor Strait, Woodlands side
    assert m is not None and m.zone == "JHR02" and not m.exact


def test_bad_input(index: ZoneIndex) -> None:
    assert index.lookup(None, 101.7) is None
    assert index.lookup("x", "y") is None


def test_bundled_file_is_compact_delta_format() -> None:
    import gzip
    import json

    from custom_components.esolatgps.zones import DATA_FILE

    raw = DATA_FILE.read_bytes()
    assert raw[:2] == b"\x1f\x8b" and len(raw) < 200_000
    data = json.loads(gzip.decompress(raw))
    assert data["format"] == 2 and isinstance(data["districts"][0]["p"][0][0][0], int)


def test_plain_json_float_format_still_loads(tmp_path) -> None:
    """A legacy/uncompressed float file (e.g. a downloaded update) loads the same way."""
    import json

    square = [101.0, 3.0, 102.0, 3.0, 102.0, 4.0, 101.0, 4.0, 101.0, 3.0]
    data = {"version": "t", "zones": {"SGR01": {"negeri": "Selangor"}},
            "districts": [{"z": "SGR01", "d": "Test", "s": "SGR", "b": [101.0, 3.0, 102.0, 4.0], "p": [[square]]}]}
    path = tmp_path / "z.json"
    path.write_text(json.dumps(data))
    idx = ZoneIndex.load(path)
    assert idx.lookup(3.5, 101.5).zone == "SGR01"
    assert idx.zone_info("SGR01")["negeri"] == "Selangor"
