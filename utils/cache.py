"""
File-based JSON cache with TTL.

Stores scraper results as JSON files in .cache/ directory.
Each file is keyed by scraper_id + query hash. Stale entries are
ignored on read (TTL check) and cleaned up periodically.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


class FileCache:
    """
    Simple file-based cache.

    Flow: check() → hit or miss → on miss, scrape → store().
    TTL is checked on read; expired entries return None.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int | None = None,
    ):
        self.cache_dir = cache_dir or settings.cache_dir
        self.ttl = timedelta(hours=ttl_hours or settings.cache_ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, scraper_id: str, query_params: dict | None = None) -> str:
        """Generate a deterministic cache key from scraper ID + query params."""
        raw = scraper_id
        if query_params:
            # Sort keys for deterministic hashing
            raw += json.dumps(query_params, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _path_for(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(
        self, scraper_id: str, query_params: dict | None = None
    ) -> list[dict] | None:
        """
        Return cached jobs list if cache hit and not expired, else None.

        Returns raw dicts (not Job objects) to keep cache layer decoupled.
        """
        key = self._make_key(scraper_id, query_params)
        path = self._path_for(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Cache read failed for %s: %s", scraper_id, e)
            return None

        cached_at = datetime.fromisoformat(data.get("cached_at", ""))
        if datetime.now() - cached_at > self.ttl:
            logger.debug("Cache expired for %s", scraper_id)
            return None

        logger.debug("Cache hit for %s (%d jobs)", scraper_id, len(data["jobs"]))
        return data["jobs"]

    def store(
        self,
        scraper_id: str,
        jobs: list[dict],
        query_params: dict | None = None,
    ) -> None:
        """Write jobs list to cache file."""
        key = self._make_key(scraper_id, query_params)
        path = self._path_for(key)

        data = {
            "scraper_id": scraper_id,
            "cached_at": datetime.now().isoformat(),
            "job_count": len(jobs),
            "jobs": jobs,
        }

        try:
            path.write_text(json.dumps(data, default=str))
            logger.debug("Cached %d jobs for %s", len(jobs), scraper_id)
        except OSError as e:
            logger.warning("Cache write failed for %s: %s", scraper_id, e)

    def invalidate(self, scraper_id: str, query_params: dict | None = None) -> None:
        """Remove a specific cache entry."""
        key = self._make_key(scraper_id, query_params)
        path = self._path_for(key)
        if path.exists():
            path.unlink()

    def clear(self) -> int:
        """Remove all cache files. Returns count of files removed."""
        count = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count
