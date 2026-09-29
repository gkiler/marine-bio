"""
Tests for the Job schema and the file cache.
"""

import json
from datetime import datetime, timedelta

from core.schemas import Job, ScraperResult
from utils.cache import FileCache


def make_job(**kw):
    fields = dict(
        job_id="test_1",
        title="Aquarist",
        employer="Ocean Lab",
        description="Animal care.",
        job_type="full-time",
        url="https://example.org/job",
        source="test",
    )
    fields.update(kw)
    return Job(**fields)


# --- Job.location_display ---


def test_location_city_and_state():
    assert make_job(location_city="Monterey", location_state="CA").location_display == "Monterey, CA"


def test_location_remote_with_place():
    job = make_job(location_city="Miami", location_state="FL", remote=True)
    assert job.location_display == "Miami, FL (Remote)"


def test_location_remote_without_place():
    assert make_job(remote=True).location_display == "Remote"


def test_location_falls_back_to_country():
    assert make_job().location_display == "USA"


def test_scraper_result_success_tracks_errors():
    assert ScraperResult(source="test").success
    assert not ScraperResult(source="test", errors=["timeout"]).success


# --- FileCache ---


def test_cache_round_trip(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    jobs = [make_job().model_dump(mode="json")]
    cache.store("test", jobs, {"q": "kelp"})
    assert cache.get("test", {"q": "kelp"}) == jobs


def test_cache_key_depends_on_query(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.store("test", [], {"q": "kelp"})
    assert cache.get("test", {"q": "coral"}) is None


def test_cache_expired_entry_is_a_miss(tmp_path):
    cache = FileCache(cache_dir=tmp_path, ttl_hours=1)
    cache.store("test", [])
    path = next(tmp_path.glob("*.json"))
    data = json.loads(path.read_text())
    data["cached_at"] = (datetime.now() - timedelta(hours=2)).isoformat()
    path.write_text(json.dumps(data))
    assert cache.get("test") is None


def test_cache_corrupt_file_is_a_miss(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.store("test", [])
    next(tmp_path.glob("*.json")).write_text("{not json")
    assert cache.get("test") is None


def test_cache_clear_removes_entries(tmp_path):
    cache = FileCache(cache_dir=tmp_path)
    cache.store("a", [])
    cache.store("b", [])
    assert cache.clear() == 2
    assert cache.get("a") is None
