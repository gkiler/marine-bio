"""
Gemini-powered relevance scorer for job listings.

Flow:
1. Pre-filter: auto-score obviously senior jobs as 1 (skip Gemini call)
2. Batch remaining jobs (100 per prompt) and score 1-10 via Gemini
3. Return (job, score) pairs sorted by score descending

Why batch: Gemini has a 1M token context window. 100 jobs at ~80 tokens
each ≈ 8k input tokens per call. 490 jobs → ~5 API calls instead of 490.
"""

import logging
import re
import time

from google import genai
from tqdm import tqdm

from config.settings import settings
from core.schemas import Job

logger = logging.getLogger(__name__)

# Jobs matching these title keywords get auto-scored as 1 (skip Gemini).
# Roman numeral levels III+ and "lead"/"supervisor" indicate senior roles.
SENIOR_TITLE_SIGNALS = [
    "senior",
    "director",
    "manager",
    "principal",
    "chief",
    "head of",
    "vice president",
    "vp ",
    "lead ",
    "supervisor",
    " iii",
    " iv",
    " v ",
]

BATCH_SIZE = 100  # Jobs per Gemini call (fits easily in context window)


def _is_obviously_senior(job: Job) -> bool:
    """Check if job title contains senior-level signals."""
    title_lower = job.title.lower()
    return any(signal in title_lower for signal in SENIOR_TITLE_SIGNALS)


def _build_batch_prompt(batch: list[Job], criteria: str) -> str:
    """
    Build a single prompt that asks Gemini to score multiple jobs at once.

    Each job gets a numbered entry. Gemini responds with one "N: score" per line.
    Description truncated to 200 chars to keep prompt compact.
    """
    lines = [
        "Score each job listing for relevance to the criteria below.",
        "Rate each 1-10 (10 = perfect match).",
        "Respond with ONLY one line per job in the format: N: score",
        "",
        f"Criteria: {criteria}",
        "",
    ]
    for i, job in enumerate(batch, 1):
        snippet = (job.description[:200] + "...") if len(job.description) > 200 else job.description
        lines.append(
            f"{i}. {job.title} | {job.employer} | {job.location_display} | "
            f"{job.job_type} | {snippet}"
        )
    return "\n".join(lines)


def _parse_batch_response(text: str, batch_size: int) -> list[int]:
    """
    Parse Gemini's batch response into a list of scores.

    Expected format: "1: 7\n2: 3\n3: 10\n..."
    Returns list of scores aligned with batch indices.
    Missing entries default to 5 (mid-range).
    """
    scores = [5] * batch_size  # Default for any unparsed jobs
    for line in text.strip().splitlines():
        match = re.match(r"(\d+)\s*[:.\-)\s]\s*(\d+)", line.strip())
        if match:
            idx = int(match.group(1)) - 1  # Convert 1-indexed to 0-indexed
            score = int(match.group(2))
            if 0 <= idx < batch_size:
                scores[idx] = max(1, min(10, score))
    return scores


def _score_batch(
    client: genai.Client, batch: list[Job], criteria: str, usage: dict[str, int]
) -> list[int]:
    """
    Score a batch of jobs in a single Gemini call.

    Returns list of int scores aligned with batch order.
    Retries with exponential backoff on rate limit errors.
    """
    prompt = _build_batch_prompt(batch, criteria)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )

            # Track token usage
            meta = getattr(response, "usage_metadata", None)
            if meta:
                usage["prompt_tokens"] += getattr(meta, "prompt_token_count", 0) or 0
                usage["candidates_tokens"] += getattr(meta, "candidates_token_count", 0) or 0
                usage["cached_tokens"] += getattr(meta, "cached_content_token_count", 0) or 0
                usage["total_tokens"] += getattr(meta, "total_token_count", 0) or 0
            usage["api_calls"] += 1

            return _parse_batch_response(response.text, len(batch))
        except Exception as e:
            is_rate_limit = "429" in str(e) or "quota" in str(e).lower()
            if is_rate_limit and attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.warning("Rate limited, retrying in %ds", delay)
                time.sleep(delay)
            else:
                logger.warning("Gemini batch scoring failed: %s", e)
                return [5] * len(batch)
    return [5] * len(batch)


def score_jobs(jobs: list[Job], criteria: str) -> list[tuple[Job, int]]:
    """
    Score each job 1-10 against user criteria using Gemini.

    Flow:
    1. Pre-filter: skip obviously senior jobs (auto-score 1)
    2. Batch remaining jobs (100 per prompt) and score via Gemini
    3. Return (job, score) pairs sorted by score descending

    Requires GEMINI_API_KEY in environment. If missing, all jobs get score 5.
    """
    if not settings.gemini_api_key:
        logger.warning("No GEMINI_API_KEY — all jobs will receive score 5")
        return sorted(
            [(job, 5) for job in jobs],
            key=lambda pair: pair[1],
            reverse=True,
        )

    client = genai.Client(api_key=settings.gemini_api_key)
    scored: list[tuple[Job, int]] = []
    to_score: list[Job] = []
    usage: dict[str, int] = {
        "prompt_tokens": 0,
        "candidates_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
        "api_calls": 0,
    }

    # Pass 1: pre-filter
    for job in jobs:
        if _is_obviously_senior(job):
            scored.append((job, 1))
        else:
            to_score.append(job)

    skipped = len(jobs) - len(to_score)
    if skipped:
        print(f"  Pre-filter: {skipped} obviously senior jobs auto-scored as 1")

    # Pass 2: batch Gemini scoring with progress bar
    def _running_cost() -> float:
        return (
            usage["prompt_tokens"] * 0.50 / 1_000_000
            + usage["candidates_tokens"] * 3.00 / 1_000_000
            + usage["cached_tokens"] * 0.05 / 1_000_000
        )

    total_batches = (len(to_score) + BATCH_SIZE - 1) // BATCH_SIZE
    pbar = tqdm(total=len(to_score), desc="Scoring", unit="job")
    for i in range(0, len(to_score), BATCH_SIZE):
        batch = to_score[i : i + BATCH_SIZE]
        batch_scores = _score_batch(client, batch, criteria, usage)
        for job, score in zip(batch, batch_scores):
            scored.append((job, score))
        pbar.update(len(batch))
        pbar.set_postfix_str(f"${_running_cost():.4f}")
    pbar.close()

    # Final cost summary
    cost = _running_cost()
    input_cost = usage["prompt_tokens"] * 0.50 / 1_000_000
    output_cost = usage["candidates_tokens"] * 3.00 / 1_000_000
    cache_cost = usage["cached_tokens"] * 0.05 / 1_000_000
    print(f"\n  Gemini: {usage['api_calls']} calls, {usage['total_tokens']:,} tokens, "
          f"${cost:.4f} (${input_cost:.4f} in + ${output_cost:.4f} out + ${cache_cost:.4f} cache)")

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
