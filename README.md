# Marine Bio Job Finder

Entry-level marine biology jobs are spread across dozens of small boards, aquarium
sites, research institutes and agency portals that don't share a search. This tool
pulls them into one list, removes duplicates, and flags which postings suit a recent
bachelor's graduate.

## How it works

1. **Scrape.** 30 sources, one scraper each: the USAJOBS API, marine and
   conservation job boards, aquariums and zoos, research institutes (WHOI, Scripps,
   MBARI, Mote), NGOs, EPA, BOEM, Florida state jobs, and academic boards. Every
   scraper subclasses `BaseScraper`, which handles a per-source token-bucket rate
   limit (10 requests a minute by default), retries with backoff, and a 6-hour file
   cache. Sites that only render with JavaScript use Playwright; the ones that still
   can't be read report an error in the results instead of returning nothing.
2. **Run in parallel.** `scraper_manager` runs the scrapers on a thread pool and
   collects per-source results, errors and timings.
3. **Deduplicate.** The same posting often appears on several boards. Jobs are
   matched on normalized employer and title, and the copy with the longest
   description is kept.
4. **Classify.** A keyword pass labels clear cases (technician, internship,
   seasonal vs. senior, director, 5+ years). Only the ambiguous ones go to Gemini,
   which answers whether the role fits a recent graduate.
5. **Score (optional).** `generate_html.py --filter "..."` ranks jobs 1 to 10 against
   free-text criteria, or a resume via `--filter-file`. Obviously senior titles are
   scored 1 without a model call, and the rest go to Gemini 100 per prompt, with
   token usage printed at the end.

## Run it

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # add a Gemini key; a USAJOBS key enables that source

streamlit run app.py        # filterable UI: source, state, job type, entry-level, keyword
python3 generate_html.py    # one self-contained page at docs/index.html
python3 generate_html.py --filter "entry-level fieldwork, West Coast"
```

Without a Gemini key, ambiguous jobs are shown rather than hidden, and scoring gives
every job a 5.

## Layout

```
app.py              Streamlit UI
generate_html.py    static page generator with optional scoring
scrapers/           one module per source, plus base_scraper and scraper_manager
services/           deduplicator, job_classifier, job_scorer
core/               Job and ScraperResult models (pydantic), exceptions
config/             source list and settings
utils/              rate limiter, file cache
tests/              unit tests; parser tests use small synthetic fixtures
```

## Tests

```bash
python3 -m pytest
```

The tests cover deduplication, keyword classification, the scorer's prompt and
response parsing, the cache, and the USAJOBS and Conservation Job Board parsers.
They make no network or model calls.

