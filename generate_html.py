"""
Generate a self-contained static HTML page of marine biology jobs.

Flow:
1. Import and run all scrapers
2. Optionally score jobs against user criteria via Gemini (--filter / --filter-file)
3. Sort by relevance score (if scored) or posted date (newest first)
4. Render into a single index.html with embedded CSS + vanilla JS filters

Run:
  python3 generate_html.py                                    # no scoring
  python3 generate_html.py --filter "entry-level marine bio"  # with scoring
  python3 generate_html.py --filter-file criteria.txt         # criteria from file

Output: docs/index.html
"""

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

# Import all scrapers to trigger @register_scraper
from scrapers import (  # noqa: F401
    usajobs_scraper,
    conservation_scraper,
    bluejobs_scraper,
    schmidt_scraper,
    climatebase_scraper,
    sevenseas_scraper,
    wiseoceans_scraper,
    aza_scraper,
    aquariumshiring_scraper,
    mote_scraper,
    whoi_scraper,
    scripps_scraper,
    mbari_scraper,
    afs_scraper,
    aslo_scraper,
    smm_scraper,
    oceana_scraper,
    ocean_conservancy_scraper,
    tnc_scraper,
    wwf_scraper,
    wcs_scraper,
    epa_scraper,
    boem_scraper,
    florida_gov_scraper,
    nature_careers_scraper,
    science_careers_scraper,
    ecojobs_scraper,
    envcareer_scraper,
    idealist_scraper,
    academic_scraper,
)
from config.sources import SOURCES
from scrapers.scraper_manager import run_all_scrapers


def _source_name(scraper_id: str) -> str:
    """Map scraper_id to human-readable name."""
    for s in SOURCES:
        if s.scraper_id == scraper_id:
            return s.name
    return scraper_id


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate(criteria: str | None = None) -> str:
    """
    Run scrapers, optionally score with Gemini, and return self-contained HTML.

    If criteria is provided, jobs are scored 1-10 via Gemini and sorted by
    relevance. Otherwise, sorted by posted date (current behavior).
    """
    print("Running scrapers...")
    t0 = time.time()
    jobs, results = run_all_scrapers(classify=False)
    elapsed = time.time() - t0

    ok_count = sum(1 for r in results if r.success)
    print(f"  {len(jobs)} unique jobs from {ok_count} sources in {elapsed:.1f}s")

    # Score jobs if criteria provided
    has_scores = False
    scores: dict[str, int] = {}  # job_id -> score
    if criteria:
        from services.job_scorer import score_jobs

        print(f"Scoring jobs against: {criteria[:80]}...")
        scored_pairs = score_jobs(jobs, criteria)
        # Rebuild jobs list in scored order
        jobs = [pair[0] for pair in scored_pairs]
        scores = {pair[0].job_id: pair[1] for pair in scored_pairs}
        has_scores = True
        print(f"  Scoring complete. Top score: {scored_pairs[0][1] if scored_pairs else 'N/A'}")
    else:
        # Sort: newest first (jobs without dates go last)
        jobs.sort(
            key=lambda j: j.posted_date or datetime.min,
            reverse=True,
        )

    # Collect unique values for filters
    sources = sorted({j.source for j in jobs})
    job_types = sorted({j.job_type for j in jobs})

    # Serialize jobs to JSON for the JS filter engine.
    # The esc() JS function handles display escaping via textContent,
    # so the data here only needs to be valid JSON.
    jobs_data = []
    for j in jobs:
        entry = {
            "title": j.title,
            "employer": j.employer,
            "location": j.location_display,
            "url": j.url,
            "source": j.source,
            "source_name": _source_name(j.source),
            "job_type": j.job_type,
            "posted": j.posted_date.strftime("%Y-%m-%d") if j.posted_date else "",
            "description": j.description[:300] if j.description else "",
        }
        if has_scores:
            entry["score"] = scores.get(j.job_id, 5)
        jobs_data.append(entry)

    jobs_json = json.dumps(jobs_data, ensure_ascii=False)

    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    source_checkboxes = "\n".join(
        f'            <label><input type="checkbox" value="{s}" checked> {_escape(_source_name(s))}</label>'
        for s in sources
    )
    type_checkboxes = "\n".join(
        f'            <label><input type="checkbox" value="{t}" checked> {_escape(t.title())}</label>'
        for t in job_types
    )

    # Header subtitle — include criteria if scoring was applied
    subtitle_parts = [
        f"{len(jobs)} jobs from {ok_count} sources",
        f"Updated {generated_at}",
    ]
    subtitle = " &middot; ".join(subtitle_parts)

    criteria_html = ""
    if criteria:
        criteria_html = f'\n  <p style="opacity:0.75; font-size:0.8rem; margin-top:0.25rem;">Filtered: {_escape(criteria[:120])}</p>'

    # Build sources list — all sources with status (scraped vs failed vs disabled)
    result_by_source = {r.source: r for r in results}
    sources_list_items = []
    for s in SOURCES:
        r = result_by_source.get(s.scraper_id)
        job_count = len(r.jobs) if r and r.success else 0
        if r and r.success:
            status = f'<span class="src-ok">{job_count} jobs</span>'
        elif r and not r.success:
            status = '<span class="src-fail">scrape failed</span>'
        else:
            status = '<span class="src-fail">no scraper ran</span>'
        sources_list_items.append(
            f'      <li><a href="{_escape(s.base_url)}" target="_blank" rel="noopener">'
            f'{_escape(s.name)}</a> {status}</li>'
        )
    sources_list_html = "\n".join(sources_list_items)

    # Sort toggle — only shown when scores exist
    sort_toggle_html = ""
    if has_scores:
        sort_toggle_html = """
    <div class="sort-toggle">
      <span>Sort by:</span>
      <button id="sortRelevance" class="sort-btn active" onclick="setSort('relevance')">Relevance</button>
      <button id="sortDate" class="sort-btn" onclick="setSort('date')">Date</button>
    </div>"""

    # Build HTML page.
    # XSS note: all dynamic content rendered via JS uses safe DOM methods
    # (textContent assignment), not innerHTML with user data.
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Marine Bio Jobs</title>
<style>
  :root {{
    --blue: #0077b6;
    --light-blue: #caf0f8;
    --dark: #1a1a2e;
    --gray: #6c757d;
    --bg: #f8f9fa;
    --card-bg: #fff;
    --border: #dee2e6;
    --score-high: #198754;
    --score-mid: #b5890a;
    --score-low: #adb5bd;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--dark);
    line-height: 1.5;
  }}
  header {{
    background: var(--blue);
    color: #fff;
    padding: 1.5rem;
    text-align: center;
  }}
  header h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
  header p {{ opacity: 0.85; font-size: 0.9rem; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 1rem; }}
  .filters {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: flex-start;
  }}
  .filters input[type="text"] {{
    flex: 1 1 200px;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 0.95rem;
  }}
  .filter-group {{ position: relative; }}
  .filter-group button {{
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: #fff;
    cursor: pointer;
    font-size: 0.9rem;
  }}
  .filter-dropdown {{
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.5rem;
    z-index: 10;
    max-height: 300px;
    overflow-y: auto;
    min-width: 220px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }}
  .filter-dropdown.open {{ display: block; }}
  .filter-dropdown label {{
    display: block;
    padding: 0.2rem 0.25rem;
    font-size: 0.85rem;
    cursor: pointer;
    white-space: nowrap;
  }}
  .sort-toggle {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85rem;
    color: var(--gray);
  }}
  .sort-btn {{
    padding: 0.3rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: 5px;
    background: #fff;
    cursor: pointer;
    font-size: 0.82rem;
    color: var(--gray);
  }}
  .sort-btn.active {{
    background: var(--blue);
    color: #fff;
    border-color: var(--blue);
  }}
  #count {{
    font-size: 0.9rem;
    color: var(--gray);
    margin-bottom: 0.75rem;
  }}
  .job {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.6rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    transition: border-color 0.15s;
    cursor: pointer;
  }}
  .job:hover {{ border-color: var(--blue); }}
  .job-main {{ flex: 1; min-width: 0; }}
  .job-title {{
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 0.15rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .job-title a {{ color: var(--dark); text-decoration: none; }}
  .job-title a:hover {{ color: var(--blue); text-decoration: underline; }}
  .score-badge {{
    display: inline-block;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #fff;
    flex-shrink: 0;
  }}
  .score-high {{ background: var(--score-high); }}
  .score-mid {{ background: var(--score-mid); }}
  .score-low {{ background: var(--score-low); }}
  .job-employer {{ color: var(--gray); font-size: 0.9rem; }}
  .job-meta {{
    font-size: 0.8rem;
    color: var(--gray);
    margin-top: 0.3rem;
  }}
  .job-meta span {{ margin-right: 0.75rem; }}
  .job-desc {{
    font-size: 0.85rem;
    color: #555;
    margin-top: 0.4rem;
    display: none;
  }}
  .job.expanded .job-desc {{ display: block; }}
  .job-side {{
    text-align: right;
    flex-shrink: 0;
    min-width: 100px;
  }}
  .job-source {{ font-size: 0.75rem; color: var(--gray); }}
  .job-date {{ font-size: 0.75rem; color: var(--gray); }}
  .apply-btn {{
    display: inline-block;
    margin-top: 0.4rem;
    padding: 0.3rem 0.9rem;
    background: var(--blue);
    color: #fff;
    border-radius: 5px;
    text-decoration: none;
    font-size: 0.8rem;
  }}
  .apply-btn:hover {{ opacity: 0.9; }}
  .no-results {{
    text-align: center;
    padding: 2rem;
    color: var(--gray);
  }}
  .sources-section {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-top: 2rem;
  }}
  .sources-section h2 {{
    font-size: 1rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
  }}
  .sources-section ul {{
    list-style: none;
    columns: 2;
    gap: 0.3rem;
    font-size: 0.85rem;
  }}
  .sources-section li {{
    padding: 0.15rem 0;
    break-inside: avoid;
  }}
  .sources-section.collapsed ul {{ display: none; }}
  .sources-section a {{ color: var(--blue); text-decoration: none; }}
  .sources-section a:hover {{ text-decoration: underline; }}
  .src-ok {{ color: var(--score-high); font-size: 0.75rem; }}
  .src-fail {{ color: #dc3545; font-size: 0.75rem; }}
  footer {{
    text-align: center;
    padding: 2rem 1rem;
    color: var(--gray);
    font-size: 0.8rem;
  }}
  @media (max-width: 600px) {{
    .job {{ flex-direction: column; }}
    .job-side {{ text-align: left; }}
    .filters {{ flex-direction: column; }}
  }}
</style>
</head>
<body>
<header>
  <h1>Marine Bio Jobs</h1>
  <p>{subtitle}</p>{criteria_html}
</header>
<div class="container">
  <div class="filters">
    <input type="text" id="search" placeholder="Search jobs..." autofocus>
    <div class="filter-group">
      <button onclick="toggleDropdown('sourceDropdown')">Sources</button>
      <div id="sourceDropdown" class="filter-dropdown">
        <label><input type="checkbox" id="srcAll" checked onchange="toggleAll('source', this.checked)"> <strong>All</strong></label>
{source_checkboxes}
      </div>
    </div>
    <div class="filter-group">
      <button onclick="toggleDropdown('typeDropdown')">Job Type</button>
      <div id="typeDropdown" class="filter-dropdown">
        <label><input type="checkbox" id="typeAll" checked onchange="toggleAll('type', this.checked)"> <strong>All</strong></label>
{type_checkboxes}
      </div>
    </div>{sort_toggle_html}
  </div>
  <div id="count"></div>
  <div id="jobs"></div>
  <div class="sources-section">
    <h2 onclick="this.parentElement.classList.toggle('collapsed')">All Sources ({len(SOURCES)})</h2>
    <ul id="sourcesList">
{sources_list_html}
    </ul>
  </div>
</div>
<footer>
  Data scraped from {ok_count} marine biology job sources.
</footer>
<script>
const JOBS = {jobs_json};
const HAS_SCORES = {'true' if has_scores else 'false'};
let currentSort = HAS_SCORES ? 'relevance' : 'date';

const searchEl = document.getElementById('search');
const jobsEl = document.getElementById('jobs');
const countEl = document.getElementById('count');

function getChecked(dropdownId) {{
  const dd = document.getElementById(dropdownId);
  return [...dd.querySelectorAll('input[type=checkbox][value]')]
    .filter(cb => cb.checked)
    .map(cb => cb.value);
}}

function toggleDropdown(id) {{
  document.querySelectorAll('.filter-dropdown').forEach(d => {{
    if (d.id !== id) d.classList.remove('open');
  }});
  document.getElementById(id).classList.toggle('open');
}}

function toggleAll(group, checked) {{
  const dd = group === 'source' ? 'sourceDropdown' : 'typeDropdown';
  document.getElementById(dd)
    .querySelectorAll('input[type=checkbox][value]')
    .forEach(cb => cb.checked = checked);
  render();
}}

function setSort(mode) {{
  currentSort = mode;
  if (HAS_SCORES) {{
    document.getElementById('sortRelevance').className = 'sort-btn' + (mode === 'relevance' ? ' active' : '');
    document.getElementById('sortDate').className = 'sort-btn' + (mode === 'date' ? ' active' : '');
  }}
  render();
}}

document.addEventListener('click', e => {{
  if (!e.target.closest('.filter-group')) {{
    document.querySelectorAll('.filter-dropdown').forEach(d => d.classList.remove('open'));
  }}
}});

function scoreClass(s) {{
  if (s >= 8) return 'score-high';
  if (s >= 5) return 'score-mid';
  return 'score-low';
}}

function render() {{
  const q = searchEl.value.toLowerCase().trim();
  const sources = new Set(getChecked('sourceDropdown'));
  const types = new Set(getChecked('typeDropdown'));

  let filtered = JOBS.filter(j => {{
    if (!sources.has(j.source)) return false;
    if (!types.has(j.job_type)) return false;
    if (q && !(j.title + ' ' + j.employer + ' ' + j.location + ' ' + j.description).toLowerCase().includes(q)) return false;
    return true;
  }});

  /* Sort: relevance (score desc) or date (newest first) */
  if (currentSort === 'relevance' && HAS_SCORES) {{
    filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
  }} else {{
    filtered.sort((a, b) => {{
      if (!a.posted && !b.posted) return 0;
      if (!a.posted) return 1;
      if (!b.posted) return -1;
      return b.posted.localeCompare(a.posted);
    }});
  }}

  countEl.textContent = 'Showing ' + filtered.length + ' of ' + JOBS.length + ' jobs';

  if (!filtered.length) {{
    jobsEl.textContent = '';
    const msg = document.createElement('div');
    msg.className = 'no-results';
    msg.textContent = 'No jobs match your filters.';
    jobsEl.appendChild(msg);
    return;
  }}

  /* Build job cards using safe DOM methods. */
  jobsEl.textContent = '';
  filtered.forEach(j => {{
    const card = document.createElement('div');
    card.className = 'job';
    card.onclick = () => card.classList.toggle('expanded');

    const main = document.createElement('div');
    main.className = 'job-main';

    const titleDiv = document.createElement('div');
    titleDiv.className = 'job-title';
    const titleLink = document.createElement('a');
    titleLink.href = j.url;
    titleLink.target = '_blank';
    titleLink.rel = 'noopener';
    titleLink.textContent = j.title;
    titleLink.onclick = e => e.stopPropagation();
    titleDiv.appendChild(titleLink);

    if (HAS_SCORES && j.score != null) {{
      const badge = document.createElement('span');
      badge.className = 'score-badge ' + scoreClass(j.score);
      badge.textContent = j.score + '/10';
      titleDiv.appendChild(badge);
    }}

    main.appendChild(titleDiv);

    const emp = document.createElement('div');
    emp.className = 'job-employer';
    emp.textContent = j.employer;
    main.appendChild(emp);

    const meta = document.createElement('div');
    meta.className = 'job-meta';
    const locSpan = document.createElement('span');
    locSpan.textContent = j.location;
    meta.appendChild(locSpan);
    const typeSpan = document.createElement('span');
    typeSpan.textContent = j.job_type;
    meta.appendChild(typeSpan);
    main.appendChild(meta);

    const desc = document.createElement('div');
    desc.className = 'job-desc';
    desc.textContent = j.description;
    main.appendChild(desc);

    card.appendChild(main);

    const side = document.createElement('div');
    side.className = 'job-side';
    const src = document.createElement('div');
    src.className = 'job-source';
    src.textContent = 'via ' + j.source_name;
    side.appendChild(src);
    if (j.posted) {{
      const dt = document.createElement('div');
      dt.className = 'job-date';
      dt.textContent = j.posted;
      side.appendChild(dt);
    }}
    const btn = document.createElement('a');
    btn.className = 'apply-btn';
    btn.href = j.url;
    btn.target = '_blank';
    btn.rel = 'noopener';
    btn.textContent = 'Apply';
    btn.onclick = e => e.stopPropagation();
    side.appendChild(btn);

    card.appendChild(side);
    jobsEl.appendChild(card);
  }});
}}

searchEl.addEventListener('input', render);
document.querySelectorAll('.filter-dropdown input').forEach(cb => cb.addEventListener('change', render));
render();
</script>
</body>
</html>"""
    return html


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate static HTML page of marine biology jobs."
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Criteria for Gemini relevance scoring (e.g. 'entry-level marine biology')",
    )
    parser.add_argument(
        "--filter-file",
        type=str,
        default=None,
        help="Path to file containing scoring criteria (for longer prompts like resume text)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    # Resolve criteria: --filter takes precedence, --filter-file as fallback
    criteria = None
    if args.filter:
        criteria = args.filter
    elif args.filter_file:
        criteria_path = Path(args.filter_file)
        if not criteria_path.exists():
            raise FileNotFoundError(f"Filter file not found: {args.filter_file}")
        criteria = criteria_path.read_text(encoding="utf-8").strip()

    docs = Path(__file__).parent / "docs"
    docs.mkdir(exist_ok=True)
    html = generate(criteria)
    out = docs / "index.html"
    out.write_text(html, encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"Wrote {out} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
