"""
Entry-level job classifier.

Two-pass approach:
1. Keyword filter (fast, no AI) — catches obvious entry-level / senior signals
2. Gemini classifier (for ambiguous jobs) — asks LLM if suitable for recent grad

Why two passes: most jobs can be classified by keywords alone, saving API calls.
Gemini is only used when keyword signals are mixed or absent.
"""

import logging

from google import genai

from config.settings import settings
from core.schemas import Job

logger = logging.getLogger(__name__)

# Signals that a job IS entry-level
POSITIVE_SIGNALS = [
    "entry level",
    "entry-level",
    "junior",
    "assistant",
    "technician",
    "intern",
    "internship",
    "volunteer",
    "field assistant",
    "lab tech",
    "lab technician",
    "seasonal",
    "recent graduate",
    "new graduate",
    "0-2 years",
    "0-1 years",
    "no experience required",
    "bachelor",
]

# Signals that a job is NOT entry-level
NEGATIVE_SIGNALS = [
    "senior",
    "director",
    "manager",
    "principal",
    "lead scientist",
    "chief",
    "head of",
    "10+ years",
    "8+ years",
    "7+ years",
    "phd required",
    "doctorate required",
    "5+ years experience",
    "extensive experience",
]


def classify_by_keywords(job: Job) -> bool | None:
    """
    Fast keyword-based classification.

    Returns True (entry-level), False (senior), or None (ambiguous).
    Checks title first (strongest signal), then description.
    """
    text = f"{job.title} {job.description}".lower()

    has_positive = any(signal in text for signal in POSITIVE_SIGNALS)
    has_negative = any(signal in text for signal in NEGATIVE_SIGNALS)

    if has_positive and not has_negative:
        return True
    if has_negative and not has_positive:
        return False
    # Both signals or neither — ambiguous
    return None


def classify_batch_with_gemini(jobs: list[Job]) -> list[bool]:
    """
    Use Gemini to classify ambiguous jobs as entry-level or not.

    Sends title + first 500 chars of description per job.
    Returns list of booleans aligned with input list.
    """
    if not settings.gemini_api_key:
        logger.warning("No GEMINI_API_KEY — skipping AI classification")
        return [True] * len(jobs)  # Default to showing the job

    client = genai.Client(api_key=settings.gemini_api_key)

    results = []
    for job in jobs:
        snippet = job.description[:500]
        prompt = (
            "You are classifying job listings for a recent marine biology "
            "bachelor's graduate. Answer ONLY 'yes' or 'no'.\n\n"
            f"Job title: {job.title}\n"
            f"Employer: {job.employer}\n"
            f"Description: {snippet}\n\n"
            "Is this job suitable for a recent marine biology bachelor's graduate "
            "with no professional experience beyond internships?"
        )

        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )
            answer = response.text.strip().lower()
            results.append(answer.startswith("yes"))
        except Exception as e:
            logger.warning("Gemini classification failed for %s: %s", job.job_id, e)
            results.append(True)  # Default to showing the job

    return results


def classify_jobs(jobs: list[Job]) -> list[Job]:
    """
    Classify all jobs as entry-level or not.

    Flow:
    1. Run keyword filter on all jobs
    2. Collect ambiguous jobs (keyword returned None)
    3. Send ambiguous batch to Gemini
    4. Merge results back

    Returns new Job objects with is_entry_level set (immutable pattern).
    """
    ambiguous_indices: list[int] = []
    classified: list[Job] = []

    # Pass 1: keyword classification
    for i, job in enumerate(jobs):
        result = classify_by_keywords(job)
        if result is not None:
            classified.append(job.model_copy(update={"is_entry_level": result}))
        else:
            classified.append(job)
            ambiguous_indices.append(i)

    # Pass 2: Gemini for ambiguous jobs
    if ambiguous_indices:
        ambiguous_jobs = [classified[i] for i in ambiguous_indices]
        logger.info(
            "Classifying %d ambiguous jobs with Gemini", len(ambiguous_jobs)
        )

        # Process in batches
        for batch_start in range(
            0, len(ambiguous_jobs), settings.classifier_batch_size
        ):
            batch = ambiguous_jobs[
                batch_start : batch_start + settings.classifier_batch_size
            ]
            batch_results = classify_batch_with_gemini(batch)

            for j, is_entry in enumerate(batch_results):
                idx = ambiguous_indices[batch_start + j]
                classified[idx] = classified[idx].model_copy(
                    update={"is_entry_level": is_entry}
                )

    return classified
