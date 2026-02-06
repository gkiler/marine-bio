"""
Cross-source job deduplication.

Jobs from different sources often refer to the same position.
We deduplicate by normalizing employer + title into a fingerprint.

Why fingerprint-based: URL comparison doesn't work across sources,
and exact title match misses minor formatting differences.
"""

import re
import logging

from core.schemas import Job

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """
    Normalize text for fuzzy comparison.

    Lowercases, strips punctuation, collapses whitespace.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _fingerprint(job: Job) -> str:
    """
    Generate a dedup fingerprint from employer + title.

    Two jobs with the same fingerprint are considered duplicates.
    """
    employer = _normalize(job.employer)
    title = _normalize(job.title)
    return f"{employer}|{title}"


def deduplicate(jobs: list[Job]) -> list[Job]:
    """
    Remove duplicate jobs across sources.

    When duplicates are found, keeps the one with the most detail
    (longer description). Returns a new list (immutable pattern).

    Assumption: same employer + same title = same job. This will
    occasionally merge distinct positions with identical titles at
    the same employer, which is an acceptable trade-off for MVP.
    """
    seen: dict[str, Job] = {}

    for job in jobs:
        fp = _fingerprint(job)
        if fp not in seen:
            seen[fp] = job
        else:
            existing = seen[fp]
            # Keep the one with more detail
            if len(job.description) > len(existing.description):
                seen[fp] = job
                logger.debug(
                    "Dedup: replaced %s version from %s with %s",
                    fp, existing.source, job.source,
                )

    removed = len(jobs) - len(seen)
    if removed > 0:
        logger.info("Deduplicated %d jobs (removed %d duplicates)", len(seen), removed)

    return list(seen.values())
