"""
Tests for deduplication, keyword classification, and the scorer's
prompt building and response parsing. No network or Gemini calls.
"""

from core.schemas import Job
from services.deduplicator import deduplicate
from services.job_classifier import classify_by_keywords
from services.job_scorer import (
    _build_batch_prompt,
    _is_obviously_senior,
    _parse_batch_response,
)


def make_job(title="Marine Technician", employer="Ocean Lab", description="Field work.", **kw):
    return Job(
        job_id=kw.pop("job_id", f"test_{title}_{employer}"),
        title=title,
        employer=employer,
        description=description,
        job_type=kw.pop("job_type", "full-time"),
        url=kw.pop("url", "https://example.org/job"),
        source=kw.pop("source", "test"),
        **kw,
    )


# --- deduplicate ---


def test_dedup_merges_same_employer_and_title_across_formatting():
    a = make_job(title="Marine Technician", employer="Ocean Lab, Inc.", source="a")
    b = make_job(title="marine  technician", employer="ocean lab inc", source="b")
    assert len(deduplicate([a, b])) == 1


def test_dedup_keeps_the_longer_description():
    short = make_job(description="Short.", source="a")
    long = make_job(description="A much longer description with details.", source="b")
    result = deduplicate([short, long])
    assert result == [long]


def test_dedup_keeps_distinct_titles():
    jobs = [make_job(title="Aquarist"), make_job(title="Field Technician")]
    assert len(deduplicate(jobs)) == 2


def test_dedup_does_not_mutate_input():
    jobs = [make_job(source="a"), make_job(source="b")]
    deduplicate(jobs)
    assert len(jobs) == 2


# --- classify_by_keywords ---


def test_keywords_entry_level():
    assert classify_by_keywords(make_job(title="Seasonal Field Technician")) is True


def test_keywords_senior():
    assert classify_by_keywords(make_job(title="Research Director", description="Leads the program.")) is False


def test_keywords_mixed_signals_are_ambiguous():
    job = make_job(title="Senior Technician")
    assert classify_by_keywords(job) is None


def test_keywords_no_signals_are_ambiguous():
    job = make_job(title="Marine Ecologist", description="Studies kelp forests.")
    assert classify_by_keywords(job) is None


# --- scorer helpers ---


def test_parse_batch_response_reads_mixed_separators():
    assert _parse_batch_response("1: 7\n2. 3\n3) 9", 3) == [7, 3, 9]


def test_parse_batch_response_clamps_and_defaults():
    # 12 clamps to 10, 0 clamps to 1, job 4 missing defaults to 5, index 9 ignored
    text = "1: 12\n2: 0\n3: 6\n9: 8\nnot a score line"
    assert _parse_batch_response(text, 4) == [10, 1, 6, 5]


def test_obviously_senior_titles():
    assert _is_obviously_senior(make_job(title="Senior Aquarist"))
    assert _is_obviously_senior(make_job(title="Biologist III"))
    assert not _is_obviously_senior(make_job(title="Biologist I"))
    assert not _is_obviously_senior(make_job(title="Marine Technician"))


def test_batch_prompt_numbers_jobs_and_truncates_descriptions():
    jobs = [
        make_job(title="Aquarist", description="x" * 300),
        make_job(title="Field Technician", description="Short."),
    ]
    prompt = _build_batch_prompt(jobs, "entry-level marine biology")
    assert "Criteria: entry-level marine biology" in prompt
    assert "1. Aquarist | Ocean Lab" in prompt
    assert "2. Field Technician | Ocean Lab" in prompt
    assert "x" * 200 + "..." in prompt
    assert "x" * 201 not in prompt
