"""
All job source URLs and metadata for the marine bio job aggregator.

Each source has: name, base_url, method (api/html), tier, and optional notes.
Tiers roughly indicate scraping priority and reliability.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class JobSource:
    name: str
    base_url: str
    method: str  # "api" or "html"
    tier: int
    scraper_id: str  # matches scraper filename without _scraper.py
    notes: str = ""


# fmt: off
SOURCES: list[JobSource] = [
    # Tier 1: API-based
    JobSource("USAJOBS", "https://data.usajobs.gov/api/search", "api", 1, "usajobs",
              notes="REST API, requires free API key from developer.usajobs.gov"),

    # Tier 2: Marine-specific boards
    JobSource("Conservation Job Board", "https://www.conservationjobboard.com/category/marine-biology-jobs", "html", 2, "conservation"),
    JobSource("Blue-jobs", "https://www.blue-jobs.com", "html", 2, "bluejobs"),
    JobSource("Schmidt Marine", "https://jobs.schmidtmarine.org/jobs", "html", 2, "schmidt"),
    JobSource("ClimateBase", "https://climatebase.org", "html", 2, "climatebase",
              notes="DISABLED: Requires JavaScript (React SPA)"),
    JobSource("SevenSeas Media", "https://sevenseasmedia.org/ocean-jobs", "html", 2, "sevenseas",
              notes="DISABLED: Requires JavaScript (WordPress Job Manager AJAX)"),
    JobSource("WiseOceans", "https://wiseoceans.com/jobs", "html", 2, "wiseoceans"),

    # Tier 3: Aquariums & zoos
    JobSource("AZA Jobs", "https://www.aza.org/jobs", "html", 3, "aza"),
    JobSource("Aquariums Hiring", "https://www.aquariumshiring.com", "html", 3, "aquariumshiring"),
    JobSource("Mote Marine Lab", "https://mote.org/about/employment-opportunities", "html", 3, "mote"),

    # Tier 4: Research institutions
    JobSource("Woods Hole (WHOI)", "https://careers.whoi.edu", "html", 4, "whoi"),
    JobSource("Scripps / UCSD", "https://scripps.ucsd.edu/portal/jobs", "html", 4, "scripps"),
    JobSource("MBARI", "https://www.mbari.org/about/careers", "html", 4, "mbari"),

    # Tier 5: Professional associations
    JobSource("American Fisheries Society", "https://jobs.fisheries.org", "html", 5, "afs"),
    JobSource("ASLO", "http://aslo.users.membersuite.com/community/career-center/browse-jobs", "html", 5, "aslo",
              notes="DISABLED: Requires JavaScript (MemberSuite platform)"),
    JobSource("Society for Marine Mammalogy", "https://marinemammalscience.org/professional-development/marine-mammal-science-job-openings/", "html", 5, "smm",
              notes="DISABLED: Requires JavaScript (dynamic job loading)"),

    # Tier 6: Conservation nonprofits
    JobSource("Oceana", "https://oceana.org/employment-opportunities", "html", 6, "oceana"),
    JobSource("Ocean Conservancy", "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=4786a4ca-9800-4db8-98cb-8bc9baad2b0d&ccId=19000101_000001&lang=en_US", "html", 6, "ocean_conservancy",
              notes="DISABLED: Requires JavaScript (ADP Workforce Now ATS)"),
    JobSource("The Nature Conservancy", "https://careers.tnc.org/us/en/search-results", "html", 6, "tnc",
              notes="DISABLED: Requires JavaScript (Phenom People ATS with Angular)"),
    JobSource("WWF", "https://careers-wwfus.icims.com/jobs/search", "html", 6, "wwf",
              notes="iCIMS job board"),
    JobSource("Wildlife Conservation Society", "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25965&siteid=5168#home", "html", 6, "wcs",
              notes="DISABLED: Requires JavaScript (IBM Kenexa BrassRing ATS with Angular)"),

    # Tier 7: Government (beyond USAJOBS)
    JobSource("EPA", "https://www.epa.gov/careers", "html", 7, "epa"),
    JobSource("BOEM", "https://www.boem.gov/about-boem/employment", "html", 7, "boem"),
    # NPS removed — refers to USAJOBS (already covered)
    JobSource("Florida FWC", "https://jobs.myflorida.com/search/?q=FWC", "html", 7, "florida_gov",
              notes="FWC jobs via Florida state job portal"),

    # Tier 8: Environmental / science boards
    JobSource("Nature Careers", "https://www.nature.com/naturecareers", "html", 8, "nature_careers"),
    JobSource("Science Careers (AAAS)", "https://jobs.sciencecareers.org", "html", 8, "science_careers"),
    JobSource("EcoJobs", "https://ecojobs.com/natural-resources-and-conservation-jobs/", "html", 8, "ecojobs",
              notes="Natural Resources & Conservation category"),
    JobSource("Environmental Career Center", "https://www.environmentalcareer.com", "html", 8, "envcareer"),
    JobSource("Idealist", "https://www.idealist.org/en/jobs", "html", 8, "idealist",
              notes="DISABLED: Requires JavaScript (React SPA)"),

    # Tier 9: General with marine filters
    JobSource("Indeed", "https://www.indeed.com", "html", 9, "indeed",
              notes="Search for 'marine biology' keyword"),
    JobSource("HigherEdJobs", "https://www.higheredjobs.com", "html", 9, "academic"),
]
# fmt: on


def get_sources_by_tier(tier: int) -> list[JobSource]:
    """Get all sources for a given tier number."""
    return [s for s in SOURCES if s.tier == tier]


def get_source_by_id(scraper_id: str) -> JobSource | None:
    """Look up a source by its scraper_id."""
    for s in SOURCES:
        if s.scraper_id == scraper_id:
            return s
    return None
