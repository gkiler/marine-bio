"""
Scraper orchestrator — runs all scrapers in parallel and merges results.

Flow:
1. Instantiate all registered scrapers
2. Run them concurrently via ThreadPoolExecutor
3. Merge all Job lists
4. Deduplicate across sources
5. Classify entry-level status
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.schemas import Job, ScraperResult
from scrapers.base_scraper import BaseScraper
from services.deduplicator import deduplicate
from services.job_classifier import classify_jobs

logger = logging.getLogger(__name__)

# Registry of all available scraper classes.
# Each scraper module registers itself by appending to this list on import.
SCRAPER_REGISTRY: list[type[BaseScraper]] = []


def register_scraper(cls: type[BaseScraper]) -> type[BaseScraper]:
    """Decorator to register a scraper class."""
    SCRAPER_REGISTRY.append(cls)
    return cls


def run_all_scrapers(
    scraper_ids: list[str] | None = None,
    max_workers: int = 5,
    classify: bool = True,
) -> tuple[list[Job], list[ScraperResult]]:
    """
    Run selected scrapers in parallel, deduplicate, and classify.

    Args:
        scraper_ids: Which scrapers to run (None = all registered).
        max_workers: Thread pool size for parallel scraping.
        classify: Whether to run entry-level classification.

    Returns:
        (deduplicated_jobs, raw_results_per_scraper)
    """
    # Filter to requested scrapers
    scrapers_to_run = SCRAPER_REGISTRY
    if scraper_ids:
        scrapers_to_run = [
            cls for cls in SCRAPER_REGISTRY if cls.scraper_id in scraper_ids
        ]

    if not scrapers_to_run:
        logger.warning("No scrapers to run")
        return [], []

    logger.info("Running %d scrapers with %d workers", len(scrapers_to_run), max_workers)

    all_results: list[ScraperResult] = []
    all_jobs: list[Job] = []

    # Run scrapers in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_scraper = {}
        for scraper_cls in scrapers_to_run:
            scraper = scraper_cls()
            future = executor.submit(scraper.run)
            future_to_scraper[future] = scraper

        for future in as_completed(future_to_scraper):
            scraper = future_to_scraper[future]
            try:
                result = future.result()
                all_results.append(result)
                all_jobs.extend(result.jobs)
                if result.success:
                    logger.info(
                        "%s: found %d jobs", scraper.scraper_id, len(result.jobs)
                    )
                else:
                    logger.warning(
                        "%s: failed with errors: %s",
                        scraper.scraper_id,
                        result.errors,
                    )
            except Exception as e:
                logger.error("%s: unexpected error: %s", scraper.scraper_id, e)
                all_results.append(
                    ScraperResult(source=scraper.scraper_id, errors=[str(e)])
                )
            finally:
                scraper.close()

    # Deduplicate
    jobs = deduplicate(all_jobs)

    # Classify entry-level
    if classify:
        jobs = classify_jobs(jobs)

    logger.info(
        "Total: %d jobs from %d sources (%d after dedup)",
        len(all_jobs),
        len(all_results),
        len(jobs),
    )

    return jobs, all_results
