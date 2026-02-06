"""
Marine Bio Job Finder — Streamlit UI.

Single-page job aggregator: sidebar filters + job list.
Scrapes 34 marine biology job sources, deduplicates, classifies
entry-level suitability, and presents a filterable job queue.
"""

import streamlit as st

from config.sources import SOURCES
from core.schemas import Job
from scrapers.scraper_manager import run_all_scrapers, SCRAPER_REGISTRY

# Import all scrapers so they self-register via @register_scraper
from scrapers import (  # noqa: F401
    usajobs_scraper,
    noaa_scraper,
    conservation_scraper,
    bluejobs_scraper,
    schmidt_scraper,
    climatebase_scraper,
    tamu_scraper,
    sevenseas_scraper,
    wiseoceans_scraper,
    aza_scraper,
    aquariumshiring_scraper,
    mote_scraper,
    whoi_scraper,
    scripps_scraper,
    mbari_scraper,
    afs_scraper,
    esa_scraper,
    aslo_scraper,
    smm_scraper,
    oceana_scraper,
    ocean_conservancy_scraper,
    tnc_scraper,
    wwf_scraper,
    wcs_scraper,
    epa_scraper,
    boem_scraper,
    nps_scraper,
    florida_gov_scraper,
    nature_careers_scraper,
    science_careers_scraper,
    ecojobs_scraper,
    envcareer_scraper,
    idealist_scraper,
    indeed_scraper,
    academic_scraper,
)


# --- Page config ---
st.set_page_config(
    page_title="Marine Bio Job Finder",
    page_icon="🌊",
    layout="wide",
)

# --- Constants ---
US_STATES = [
    "All", "Alabama", "Alaska", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii",
    "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska",
    "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

STATE_ABBREVS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

JOB_TYPES = ["full-time", "part-time", "internship", "volunteer", "seasonal"]
JOBS_PER_PAGE = 25

TIER_LABELS = {
    1: "API-based",
    2: "Marine-specific boards",
    3: "Aquariums & zoos",
    4: "Research institutions",
    5: "Professional associations",
    6: "Conservation nonprofits",
    7: "Government",
    8: "Science boards",
    9: "General job boards",
}


# --- Data loading ---
@st.cache_data(ttl=3600, show_spinner="Scraping job sources...")
def load_jobs(selected_scraper_ids: tuple[str, ...]) -> tuple[list[dict], list[dict]]:
    """
    Run selected scrapers and return (jobs, results) as serializable dicts.

    Wrapped in cache_data with 1-hour TTL so we don't re-scrape on every
    Streamlit rerun. The tuple input makes it hashable for caching.
    """
    scraper_ids = list(selected_scraper_ids) if selected_scraper_ids else None
    jobs, results = run_all_scrapers(scraper_ids=scraper_ids, classify=True)
    return (
        [j.model_dump(mode="json") for j in jobs],
        [r.model_dump(mode="json") for r in results],
    )


def _normalize_state(state_value: str | None) -> str | None:
    """Normalize state abbreviations to full names for filtering."""
    if not state_value:
        return None
    state_value = state_value.strip()
    if state_value.upper() in STATE_ABBREVS:
        return STATE_ABBREVS[state_value.upper()]
    return state_value


def filter_jobs(
    jobs: list[dict],
    location_state: str,
    job_types: list[str],
    entry_level_only: bool,
    keyword: str,
    selected_sources: set[str],
) -> list[dict]:
    """Apply sidebar filters to the job list. Returns a new filtered list."""
    filtered = []
    keyword_lower = keyword.lower().strip()

    for job in jobs:
        # Source filter
        if job["source"] not in selected_sources:
            continue

        # Location filter
        if location_state != "All":
            job_state = _normalize_state(job.get("location_state"))
            if job_state != location_state:
                # Also check if location is remote
                if not job.get("remote", False):
                    continue

        # Job type filter
        if job_types and job.get("job_type") not in job_types:
            continue

        # Entry-level filter
        if entry_level_only and job.get("is_entry_level") is False:
            continue

        # Keyword filter
        if keyword_lower:
            searchable = f"{job.get('title', '')} {job.get('description', '')} {job.get('employer', '')}".lower()
            if keyword_lower not in searchable:
                continue

        filtered.append(job)

    return filtered


def sort_jobs(jobs: list[dict], sort_by: str) -> list[dict]:
    """Sort jobs by the selected criterion. Returns a new sorted list."""
    if sort_by == "Newest first":
        return sorted(
            jobs,
            key=lambda j: j.get("posted_date") or "",
            reverse=True,
        )
    elif sort_by == "Employer A-Z":
        return sorted(jobs, key=lambda j: j.get("employer", "").lower())
    elif sort_by == "Source A-Z":
        return sorted(jobs, key=lambda j: j.get("source", "").lower())
    return jobs


# --- Sidebar ---
st.sidebar.title("Filters")

# Source selection grouped by tier
st.sidebar.subheader("Job Sources")
registered_ids = {cls.scraper_id for cls in SCRAPER_REGISTRY}
selected_sources: set[str] = set()

for tier_num, tier_label in TIER_LABELS.items():
    tier_sources = [s for s in SOURCES if s.tier == tier_num and s.scraper_id in registered_ids]
    if not tier_sources:
        continue

    with st.sidebar.expander(f"Tier {tier_num}: {tier_label}", expanded=(tier_num <= 3)):
        select_all = st.checkbox(f"Select all {tier_label}", value=True, key=f"tier_{tier_num}_all")
        for source in tier_sources:
            checked = st.checkbox(source.name, value=select_all, key=f"source_{source.scraper_id}")
            if checked:
                selected_sources.add(source.scraper_id)

st.sidebar.divider()

# Location filter
location_state = st.sidebar.selectbox(
    "Location (state)",
    US_STATES,
    index=US_STATES.index("Florida"),
)

# Job type filter
st.sidebar.subheader("Job Type")
selected_job_types = []
for jt in JOB_TYPES:
    if st.sidebar.checkbox(jt.title(), value=True, key=f"jt_{jt}"):
        selected_job_types.append(jt)

st.sidebar.divider()

# Entry-level toggle
entry_level_only = st.sidebar.toggle("Entry-level only", value=True)

# Keyword search
keyword = st.sidebar.text_input("Keyword search", placeholder="e.g. coral reef, GIS...")

# Refresh button
if st.sidebar.button("Refresh Jobs", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

# Sort
sort_by = st.sidebar.selectbox("Sort by", ["Newest first", "Employer A-Z", "Source A-Z"])


# --- Main area ---
st.title("Marine Bio Job Finder")
st.caption("Aggregating entry-level marine biology jobs from 34 sources")

# Load data
if not selected_sources:
    st.warning("Select at least one job source in the sidebar.")
    st.stop()

with st.spinner("Loading jobs..."):
    raw_jobs, raw_results = load_jobs(tuple(sorted(selected_sources)))

# Build source name lookup
source_names = {s.scraper_id: s.name for s in SOURCES}

# Show scraper status
successful = sum(1 for r in raw_results if not r.get("errors"))
total_sources = len(raw_results)
if total_sources > 0:
    st.caption(f"Sources: {successful}/{total_sources} responded successfully")

# Apply filters
filtered = filter_jobs(
    raw_jobs,
    location_state,
    selected_job_types,
    entry_level_only,
    keyword,
    selected_sources,
)
filtered = sort_jobs(filtered, sort_by)

# Job count header
st.subheader(f"Showing {len(filtered)} of {len(raw_jobs)} jobs")

# Pagination
total_pages = max(1, (len(filtered) + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE)
page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
start_idx = (page - 1) * JOBS_PER_PAGE
end_idx = start_idx + JOBS_PER_PAGE
page_jobs = filtered[start_idx:end_idx]

if not page_jobs:
    st.info("No jobs match your filters. Try broadening your search.")
    st.stop()

# Job cards
for job in page_jobs:
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**{job['title']}**")
            st.caption(f"{job['employer']}")

            # Location + job type badges
            location_parts = [p for p in [job.get("location_city"), job.get("location_state")] if p]
            location = ", ".join(location_parts) if location_parts else job.get("location_country", "USA")
            if job.get("remote"):
                location = f"{location} (Remote)" if location_parts else "Remote"

            badge_parts = [location]
            if job.get("salary_range"):
                badge_parts.append(job["salary_range"])
            badge_parts.append(job.get("job_type", "").title())

            st.caption(" · ".join(badge_parts))

        with col2:
            source_name = source_names.get(job["source"], job["source"])
            st.caption(f"via {source_name}")

            if job.get("posted_date"):
                date_str = job["posted_date"][:10]
                st.caption(f"Posted: {date_str}")

            st.link_button("Apply", job["url"], use_container_width=True)

        # Expandable description
        with st.expander("Details"):
            st.write(job.get("description", "No description available."))
            if job.get("requirements"):
                st.markdown("**Requirements:**")
                for req in job["requirements"]:
                    st.markdown(f"- {req}")
            if job.get("application_deadline"):
                st.caption(f"Deadline: {job['application_deadline'][:10]}")

# Pagination footer
st.caption(f"Page {page} of {total_pages}")
