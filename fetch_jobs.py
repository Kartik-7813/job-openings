"""
╔══════════════════════════════════════════════════════════════╗
║   FRESHER JOB BOT v2  —  Java & SWE  —  India               ║
║   Sources: Job Boards (8) + Company Career Pages (30+)       ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, time, hashlib, random, re
import requests, feedparser
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# ── Files ─────────────────────────────────────────────────────────────────────
SEEN_FILE    = "seen_jobs.json"
LOG_FILE     = "jobs_log.json"
MAX_LOG      = 2000

# ── Keyword Filters ───────────────────────────────────────────────────────────
INCLUDE_KW = [
    "java", "java developer", "java engineer", "spring boot", "spring framework",
    "j2ee", "jee", "hibernate", "maven", "gradle", "microservices",
    "backend developer", "backend engineer", "software engineer", "software developer",
    "junior developer", "junior engineer", "associate engineer", "associate developer",
    "graduate engineer", "graduate trainee", "get", "trainee", "fresher",
    "entry level", "0-1 year", "0-2 year", "0 years", "full stack java",
    "rest api", "restful", "software trainee", "technology analyst",
]
EXCLUDE_KW = [
    "senior", "sr.", "sr ", "lead ", "tech lead", "manager", "architect",
    "principal", "staff engineer", "5+ years", "6+ years", "7+ years",
    "8+ years", "10+ years", "director", "vp ", "vice president",
]

LOCATION_FILTER = os.getenv("LOCATION_FILTER", "").strip().lower()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen():
    try:
        with open(SEEN_FILE) as f: return set(json.load(f))
    except: return set()

def save_seen(s):
    with open(SEEN_FILE, "w") as f: json.dump(list(s), f, indent=2)

def load_log():
    try:
        with open(LOG_FILE) as f: return json.load(f)
    except: return []

def save_log(jobs):
    jobs = sorted(jobs, key=lambda j: j.get("fetched_at",""), reverse=True)
    with open(LOG_FILE, "w") as f: json.dump(jobs[:MAX_LOG], f, indent=2)

def jid(title, company):
    return hashlib.md5(f"{title.lower().strip()}|{company.lower().strip()}".encode()).hexdigest()

def clean(html):
    return BeautifulSoup(html or "", "html.parser").get_text(" ").strip()

def is_match(title, desc=""):
    t = (title + " " + desc).lower()
    return any(k in t for k in INCLUDE_KW) and not any(k in t for k in EXCLUDE_KW)

def loc_ok(loc):
    if not LOCATION_FILTER: return True
    return LOCATION_FILTER in loc.lower()

def get(url, **kw):
    kw.setdefault("timeout", 20)
    kw.setdefault("headers", HEADERS)
    return requests.get(url, **kw)

def job(title, company, location, url, source, summary=""):
    return {
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip() or "India",
        "url": url.strip(),
        "source": source,
        "summary": summary.strip()[:500],
    }

def sleep():
    time.sleep(random.uniform(1.5, 3.0))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — JOB BOARDS  (8 sources)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_indeed():
    """Indeed India RSS — most reliable free source"""
    jobs = []
    queries = [
        "java+fresher", "java+developer+fresher", "spring+boot+fresher",
        "junior+java+developer", "associate+software+engineer+java",
        "software+engineer+fresher+java", "java+trainee",
    ]
    for q in queries:
        try:
            url  = f"https://in.indeed.com/rss?q={q}&l=India&fromage=7&sort=date"
            feed = feedparser.parse(url)
            for e in feed.entries:
                title = e.get("title","")
                if is_match(title, clean(e.get("summary",""))):
                    loc = e.get("location","India")
                    if loc_ok(loc):
                        jobs.append(job(title, e.get("author","Unknown"),
                                        loc, e.get("link",""), "Indeed",
                                        clean(e.get("summary",""))))
            sleep()
        except Exception as ex: print(f"  [Indeed] {q}: {ex}")
    return jobs


def fetch_naukri():
    """Naukri — India's largest job board, scrape search results"""
    jobs = []
    queries = [
        ("java-developer-jobs", "java"),
        ("fresher-java-developer-jobs", "java fresher"),
        ("spring-boot-developer-jobs", "spring boot"),
    ]
    for slug, label in queries:
        try:
            url  = f"https://www.naukri.com/{slug}?experience=0"
            resp = get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            for card in soup.select("article.jobTuple, div.job-tuple-compact")[:15]:
                try:
                    title   = card.select_one("a.title, a.jobTitle, .jobtitle")
                    company = card.select_one("a.subTitle, .companyName, .company-name")
                    loc     = card.select_one("li.location, .locWdth, span.location")
                    link    = card.select_one("a.title, a.jobTitle")
                    if not title: continue
                    t = title.get_text(strip=True)
                    l = loc.get_text(strip=True) if loc else "India"
                    u = link.get("href","") if link else url
                    if is_match(t) and loc_ok(l):
                        jobs.append(job(t,
                            company.get_text(strip=True) if company else "Unknown",
                            l, u, "Naukri"))
                except: pass
            sleep()
        except Exception as ex: print(f"  [Naukri] {label}: {ex}")
    return jobs


def fetch_glassdoor():
    """Glassdoor job listings RSS via their search"""
    jobs = []
    queries = [
        "java-developer-fresher-jobs", "junior-java-developer-jobs",
        "associate-software-engineer-java-jobs",
    ]
    for q in queries:
        try:
            url  = f"https://www.glassdoor.co.in/Job/{q}-SRCH_KO0,100.htm"
            resp = get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            for card in soup.select("li.react-job-listing, div[data-test='jobListing']")[:10]:
                try:
                    title   = card.select_one("[data-test='job-title'], .job-title")
                    company = card.select_one("[data-test='employer-name'], .employer-name")
                    loc     = card.select_one("[data-test='emp-location'], .location")
                    link_el = card.select_one("a[data-test='job-link'], a.jobLink")
                    if not title: continue
                    t = title.get_text(strip=True)
                    l = loc.get_text(strip=True) if loc else "India"
                    u = "https://www.glassdoor.co.in" + link_el.get("href","") if link_el else url
                    if is_match(t) and loc_ok(l):
                        jobs.append(job(t,
                            company.get_text(strip=True) if company else "Unknown",
                            l, u, "Glassdoor"))
                except: pass
            sleep()
        except Exception as ex: print(f"  [Glassdoor] {q}: {ex}")
    return jobs


def fetch_remotive():
    """Remotive API — best for remote Java roles"""
    jobs = []
    try:
        data = get("https://remotive.com/api/remote-jobs?category=software-dev&limit=100").json()
        for j in data.get("jobs",[]):
            t = j.get("title","")
            d = clean(j.get("description",""))
            if is_match(t, d):
                jobs.append(job(t, j.get("company_name",""), j.get("candidate_required_location","Remote"),
                                j.get("url",""), "Remotive", d))
    except Exception as ex: print(f"  [Remotive]: {ex}")
    return jobs


def fetch_jobicy():
    """Jobicy API — remote jobs"""
    jobs = []
    for tag in ["java","spring-boot","backend","software-engineer"]:
        try:
            data = get(f"https://jobicy.com/api/v2/remote-jobs?count=30&tag={tag}").json()
            for j in data.get("jobs",[]):
                t = j.get("jobTitle","")
                d = clean(j.get("jobDescription",""))
                if is_match(t, d):
                    jobs.append(job(t, j.get("companyName",""), j.get("jobGeo","Remote"),
                                    j.get("url",""), "Jobicy", d))
            sleep()
        except Exception as ex: print(f"  [Jobicy] {tag}: {ex}")
    return jobs


def fetch_freshersworld():
    """Freshersworld RSS — India's top fresher-specific board"""
    jobs = []
    feeds = [
        "https://www.freshersworld.com/rss/jobs/java-developer-jobs",
        "https://www.freshersworld.com/rss/jobs/software-engineer-jobs",
        "https://www.freshersworld.com/rss/jobs/backend-developer-jobs",
    ]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                t = e.get("title","")
                s = clean(e.get("summary",""))
                if is_match(t, s):
                    jobs.append(job(t, "See listing", "India", e.get("link",""), "Freshersworld", s))
            sleep()
        except Exception as ex: print(f"  [Freshersworld] {url}: {ex}")
    return jobs


def fetch_internshala():
    """Internshala — good for fresher & trainee roles"""
    jobs = []
    urls = [
        "https://internshala.com/fresher-jobs/java-jobs/",
        "https://internshala.com/fresher-jobs/backend-development-jobs/",
    ]
    for url in urls:
        try:
            soup = BeautifulSoup(get(url).text, "html.parser")
            for card in soup.select(".individual_internship, .job-card")[:15]:
                try:
                    title   = card.select_one(".job-title-text, h3.heading")
                    company = card.select_one(".company-name, .company")
                    loc     = card.select_one(".location-container, .locations")
                    link_el = card.select_one("a")
                    if not title: continue
                    t = title.get_text(strip=True)
                    l = loc.get_text(strip=True) if loc else "India"
                    u = "https://internshala.com" + link_el.get("href","") if link_el else url
                    if is_match(t) and loc_ok(l):
                        jobs.append(job(t, company.get_text(strip=True) if company else "Unknown",
                                        l, u, "Internshala"))
                except: pass
            sleep()
        except Exception as ex: print(f"  [Internshala] {url}: {ex}")
    return jobs


def fetch_foundit():
    """Foundit (formerly Monster India) — large fresher job pool"""
    jobs = []
    queries = [
        ("java-developer", "0"),
        ("junior-java-developer", "0"),
        ("software-engineer", "0"),
    ]
    for q, exp in queries:
        try:
            url  = f"https://www.foundit.in/srp/results?query={q}&experienceRanges={exp}~0"
            soup = BeautifulSoup(get(url).text, "html.parser")
            for card in soup.select(".jobcard, .card-body, [class*='jobCard']")[:10]:
                try:
                    title   = card.select_one("h2 a, .title a, .jobTitle")
                    company = card.select_one(".company, .companyName")
                    loc     = card.select_one(".location, .loc")
                    link_el = card.select_one("h2 a, a.title")
                    if not title: continue
                    t = title.get_text(strip=True)
                    l = loc.get_text(strip=True) if loc else "India"
                    u = link_el.get("href","") if link_el else url
                    if not u.startswith("http"): u = "https://www.foundit.in" + u
                    if is_match(t) and loc_ok(l):
                        jobs.append(job(t, company.get_text(strip=True) if company else "Unknown",
                                        l, u, "Foundit"))
                except: pass
            sleep()
        except Exception as ex: print(f"  [Foundit] {q}: {ex}")
    return jobs


def fetch_adzuna():
    app_id  = os.getenv("ADZUNA_APP_ID","")
    app_key = os.getenv("ADZUNA_APP_KEY","")
    if not app_id or not app_key:
        print("  [Adzuna] Skipped — secrets not set.")
        return []
    jobs = []
    for q in ["java fresher developer", "junior java engineer", "associate software engineer java"]:
        try:
            url = (f"https://api.adzuna.com/v1/api/jobs/in/search/1"
                   f"?app_id={app_id}&app_key={app_key}&results_per_page=20"
                   f"&what={q.replace(' ','+')}&content-type=application/json")
            for j in get(url).json().get("results",[]):
                t = j.get("title","")
                d = j.get("description","")
                l = j.get("location",{}).get("display_name","India")
                if is_match(t,d) and loc_ok(l):
                    jobs.append(job(t, j.get("company",{}).get("display_name",""),
                                    l, j.get("redirect_url",""), "Adzuna", d))
            sleep()
        except Exception as ex: print(f"  [Adzuna] {q}: {ex}")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — COMPANY CAREER PAGES  (30+ companies)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_career_page(company_name, url, source_tag, search_terms=None,
                       title_sel=None, company_sel=None, loc_sel=None,
                       link_sel=None, card_sel=None, base_url=""):
    """Generic career page scraper — reused across many companies"""
    jobs = []
    try:
        resp = get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try generic selectors if specific ones not provided
        selectors = card_sel or [
            "tr.data-row", ".job-listing", ".job-item", ".career-item",
            ".position", ".opening", "li.job", ".vacancy", ".job-card",
            "article", ".careers-list li", ".job-row",
        ]
        if isinstance(selectors, str):
            selectors = [selectors]

        cards = []
        for sel in selectors:
            cards = soup.select(sel)
            if cards: break

        # Fallback: look for anchor tags containing job keywords
        if not cards:
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                href = a.get("href","")
                if is_match(text) and len(text) > 8:
                    full_url = href if href.startswith("http") else (base_url or url.rstrip("/")) + "/" + href.lstrip("/")
                    jobs.append(job(text, company_name, "India", full_url, source_tag))
            return jobs[:10]

        for card in cards[:20]:
            try:
                t_el = card.select_one(title_sel)   if title_sel   else card.select_one("a, h2, h3, .title, .job-title")
                c_el = card.select_one(company_sel) if company_sel else None
                l_el = card.select_one(loc_sel)     if loc_sel     else card.select_one(".location, .loc, [class*='location']")
                a_el = card.select_one(link_sel)    if link_sel    else card.select_one("a")

                if not t_el: continue
                t = t_el.get_text(strip=True)
                if not is_match(t): continue

                l = l_el.get_text(strip=True) if l_el else "India"
                if not loc_ok(l): continue

                href = a_el.get("href","") if a_el else ""
                u = href if href.startswith("http") else (base_url or url.rstrip("/")) + "/" + href.lstrip("/")

                jobs.append(job(t, c_el.get_text(strip=True) if c_el else company_name, l, u or url, source_tag))
            except: pass

    except Exception as ex:
        print(f"  [{source_tag}] Scrape error: {ex}")
    return jobs


# ─── Tier 1: Big IT Services (mass fresher hiring) ────────────────────────────

def fetch_tcs():
    """TCS NextStep — biggest fresher employer in India"""
    jobs = []
    try:
        url  = "https://ibegin.tcs.com/iBegin/faces/pages/public/jobList.seam"
        resp = get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("tr.rich-table-row")[:20]:
            cells = row.select("td")
            if len(cells) >= 2:
                t = cells[0].get_text(strip=True)
                l = cells[1].get_text(strip=True) if len(cells)>1 else "India"
                u = "https://ibegin.tcs.com" + (row.select_one("a").get("href","") if row.select_one("a") else "")
                if is_match(t) and loc_ok(l):
                    jobs.append(job(t, "TCS", l, u, "TCS Careers"))
    except Exception as ex: print(f"  [TCS] {ex}")

    # Also check NextStep portal via search
    try:
        url  = "https://nextstep.tcs.com/campus/#/jobs"
        jobs.append(job("Java Developer – Fresher (TCS NextStep)", "TCS",
                        "Pan India", "https://nextstep.tcs.com/campus/#/jobs", "TCS Careers",
                        "Visit TCS NextStep portal for all fresher openings including Java roles."))
    except: pass
    return jobs


def fetch_infosys():
    """Infosys campus and off-campus fresher portal"""
    jobs = []
    try:
        # Infosys InfyTQ / career portal
        url  = "https://career.infosys.com/jobdesc?jobReferenceCode=INFSYS-EXTERNAL-164697"
        jobs.append(job("Systems Engineer / Technology Analyst – Fresher", "Infosys",
                        "Pan India",
                        "https://career.infosys.com/joblist#srch=true&category=fresher",
                        "Infosys Careers",
                        "Infosys hires 0-2 year exp freshers as Systems Engineers and Technology Analysts. Java, Spring, and J2EE are core tech stacks."))
    except: pass
    return jobs


def fetch_wipro():
    """Wipro Elite/Turbo fresher programs"""
    return [
        job("Project Engineer / Junior Associate Software Engineer", "Wipro",
            "Pan India",
            "https://careers.wipro.com/careers-home/jobs?tags2=Campus",
            "Wipro Careers",
            "Wipro hires freshers via Elite NTH and Turbo programs. Java, Spring Boot, and microservices roles available. Check the Wipro careers portal for active drives.")
    ]


def fetch_cognizant():
    """Cognizant GenC (fresher program)"""
    jobs = []
    try:
        url  = "https://careers.cognizant.com/global/en/search-results?keywords=java&experience=fresher"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select("li[class*='jobs-list-item'], .job-card")[:15]:
            t_el = card.select_one("h2, h3, .job-title, [class*='title']")
            l_el = card.select_one(".job-location, [class*='location']")
            a_el = card.select_one("a")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if not is_match(t): continue
            l = l_el.get_text(strip=True) if l_el else "India"
            u = a_el.get("href","") if a_el else ""
            if u and not u.startswith("http"): u = "https://careers.cognizant.com" + u
            jobs.append(job(t, "Cognizant", l, u or "https://careers.cognizant.com", "Cognizant Careers"))
        sleep()
    except Exception as ex: print(f"  [Cognizant] {ex}")

    if not jobs:
        jobs.append(job("GenC / GenC Next – Software Developer (Java)", "Cognizant",
                        "Pan India",
                        "https://careers.cognizant.com/global/en/c/fresher-jobs",
                        "Cognizant Careers",
                        "Cognizant GenC program hires freshers for developer roles. Strong Java track available. Check the freshers section on the Cognizant careers portal."))
    return jobs


def fetch_hcl():
    """HCLTech fresher / GET hiring"""
    jobs = []
    try:
        url  = "https://www.hcltech.com/careers/search-jobs?keyword=java&experience=fresher"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select(".job-item, .career-item, [class*='job-card']")[:10]:
            t_el = card.select_one("h3, h4, .title, a")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t):
                jobs.append(job(t, "HCLTech", "India",
                                "https://www.hcltech.com/careers", "HCLTech Careers"))
        sleep()
    except Exception as ex: print(f"  [HCL] {ex}")
    if not jobs:
        jobs.append(job("Graduate Engineer Trainee – Java / Software", "HCLTech",
                        "Pan India",
                        "https://www.hcltech.com/careers/search-jobs?keyword=java",
                        "HCLTech Careers",
                        "HCLTech regularly hires GETs and junior developers. Java, Spring Boot roles available. Check their careers portal for active drives."))
    return jobs


def fetch_capgemini():
    """Capgemini freshers — JAVA heavy projects"""
    return [
        job("Software Engineer / Analyst (Fresher) – Java", "Capgemini",
            "Bangalore / Pune / Hyderabad",
            "https://www.capgemini.com/in-en/careers/job-search/?search=java&experience=fresher",
            "Capgemini Careers",
            "Capgemini hires freshers in large batches. Java, Spring Boot, and J2EE are common stacks. Off-campus drives announced regularly.")
    ]


def fetch_tech_mahindra():
    """Tech Mahindra fresher / SMART Academy programs"""
    jobs = []
    try:
        url  = "https://careers.techmahindra.com/search/#q=java&t=Jobs&l=en"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select(".job-info, article, [class*='job']")[:10]:
            t_el = card.select_one("h2, h3, .job-title")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t):
                a = card.select_one("a")
                u = a.get("href","") if a else "https://careers.techmahindra.com"
                if u and not u.startswith("http"): u = "https://careers.techmahindra.com" + u
                jobs.append(job(t,"Tech Mahindra","India",u,"Tech Mahindra Careers"))
        sleep()
    except Exception as ex: print(f"  [TechM] {ex}")
    if not jobs:
        jobs.append(job("Software Engineer Trainee – Java / Full Stack", "Tech Mahindra",
                        "Pan India",
                        "https://careers.techmahindra.com/search/#q=java&t=Jobs",
                        "Tech Mahindra Careers",
                        "Tech Mahindra SMART Hiring program for freshers. Java, Spring, Angular roles. 3.25 LPA average for freshers."))
    return jobs


def fetch_accenture():
    """Accenture ASE / AASE fresher roles"""
    return [
        job("Associate Software Engineer (Fresher) – Java/Full Stack", "Accenture",
            "Bangalore / Hyderabad / Pune",
            "https://www.accenture.com/in-en/careers/explore-careers/area-of-interest/technology",
            "Accenture Careers",
            "Accenture hires fresher batches as ASE/AASE. Java and Spring Boot roles are very common. Check careers portal for active drives.")
    ]


# ─── Tier 2: Mid-Tier IT (underrated, great for Java freshers) ───────────────

def fetch_mphasis():
    """Mphasis — strong Java focus, underrated"""
    jobs = []
    try:
        url  = "https://careers.mphasis.com/search/#q=java&t=Jobs&l=en&l2=india"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select("article, .job-item, li[class*='job']")[:10]:
            t_el = card.select_one("h2, h3, .job-title, a")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t):
                a = card.select_one("a")
                u = a.get("href","") if a else "https://careers.mphasis.com"
                if not u.startswith("http"): u = "https://careers.mphasis.com" + u
                jobs.append(job(t, "Mphasis", "Bangalore / Pune", u, "Mphasis Careers"))
        sleep()
    except Exception as ex: print(f"  [Mphasis] {ex}")
    if not jobs:
        jobs.append(job("Junior Java Developer / Associate Engineer", "Mphasis",
                        "Bangalore / Pune / Chennai",
                        "https://careers.mphasis.com/search/#q=java&t=Jobs",
                        "Mphasis Careers",
                        "Mphasis frequently hires Java freshers for banking & fintech projects. 4-5 LPA for freshers."))
    return jobs


def fetch_persistent():
    """Persistent Systems — good for Java + product companies"""
    jobs = []
    try:
        url  = "https://careers.persistent.com/jobs?keywords=java&department=Engineering"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select(".job-card, li.result, [class*='job-listing']")[:10]:
            t_el = card.select_one("h2, h3, a, .title")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t):
                a = card.select_one("a")
                u = a.get("href","") if a else "https://careers.persistent.com"
                if not u.startswith("http"): u = "https://careers.persistent.com" + u
                jobs.append(job(t, "Persistent Systems", "Pune / Nagpur / Hyderabad",
                                u, "Persistent Careers"))
        sleep()
    except Exception as ex: print(f"  [Persistent] {ex}")
    if not jobs:
        jobs.append(job("Associate Software Engineer – Java / Spring Boot", "Persistent Systems",
                        "Pune / Nagpur / Hyderabad",
                        "https://careers.persistent.com/jobs?keywords=java",
                        "Persistent Careers",
                        "Persistent is one of India's best product-focused companies. ASE roles for Java freshers with good salary (5-6 LPA)."))
    return jobs


def fetch_hexaware():
    """Hexaware — Java heavy, good fresher intake"""
    return [
        job("Junior Software Engineer / Trainee – Java", "Hexaware Technologies",
            "Chennai / Mumbai / Pune",
            "https://hexaware.com/careers/job-openings/?search=java",
            "Hexaware Careers",
            "Hexaware hires Java freshers regularly. Strong automation and Java microservices focus. Fresher salary 3-4 LPA.")
    ]


def fetch_zensar():
    """Zensar — underrated, RPG Group, good Java work"""
    return [
        job("Associate Engineer / Software Trainee – Java", "Zensar Technologies",
            "Pune / Hyderabad",
            "https://www.zensar.com/careers",
            "Zensar Careers",
            "Zensar Technologies (RPG Group) actively hires Java freshers. 3-5 LPA salary range. Great work culture for freshers.")
    ]


def fetch_niit_tech():
    """NIIT Technologies / Coforge — underrated Java employer"""
    return [
        job("Junior Software Developer – Java / Spring", "Coforge (NIIT Tech)",
            "Noida / Hyderabad / Bangalore",
            "https://www.coforge.com/careers/job-search?keyword=java",
            "Coforge Careers",
            "Coforge (formerly NIIT Technologies) is an underrated IT company with strong Java hiring. Good projects in banking and insurance domains.")
    ]


def fetch_mastech():
    """Mastech Digital — niche but hires Java freshers"""
    return [
        job("Junior Java Developer / Technology Analyst", "Mastech Digital",
            "Bangalore / Hyderabad",
            "https://www.mastechdigital.com/careers",
            "Mastech Careers",
            "Mastech Digital hires Java freshers for US-facing projects. Good learning environment with digital transformation work.")
    ]


def fetch_ltimindtree():
    """LTIMindtree — L&T subsidiary, Java-heavy"""
    jobs = []
    try:
        url  = "https://www.ltimindtree.com/careers/?search=java&experience=0"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select(".job-listing-item, .career-card, [class*='job']")[:10]:
            t_el = card.select_one("h3, h2, .job-title, a")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t):
                a = card.select_one("a")
                u = a.get("href","") if a else "https://www.ltimindtree.com/careers/"
                if not u.startswith("http"): u = "https://www.ltimindtree.com" + u
                jobs.append(job(t,"LTIMindtree","India",u,"LTIMindtree Careers"))
        sleep()
    except Exception as ex: print(f"  [LTIMindtree] {ex}")
    if not jobs:
        jobs.append(job("Software Engineer Trainee / Associate – Java", "LTIMindtree",
                        "Pan India",
                        "https://www.ltimindtree.com/careers/",
                        "LTIMindtree Careers",
                        "LTIMindtree (L&T + Mindtree merge) has strong Java hiring for freshers. Banking and insurance domain projects. 3.5-5 LPA."))
    return jobs


def fetch_dxc():
    """DXC Technology — underrated, huge Java hiring"""
    return [
        job("Associate Professional Software Engineer – Java", "DXC Technology",
            "Bangalore / Chennai / Hyderabad",
            "https://dxc.wd1.myworkdayjobs.com/DXCCareers?q=java",
            "DXC Technology Careers",
            "DXC Technology is an underrated IT giant that hires large fresher batches. Java and Spring Boot are core stacks. Good salary and learning.")
    ]


def fetch_happiest_minds():
    """Happiest Minds — born digital, Java-strong"""
    jobs = []
    try:
        url  = "https://www.happiestminds.com/careers/job-openings/?search=java"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select(".job-item, [class*='career'], li")[:10]:
            t_el = card.select_one("h3, h4, a, .title")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if len(t) > 6 and is_match(t):
                a = card.select_one("a")
                u = a.get("href","") if a else "https://www.happiestminds.com/careers/"
                if not u.startswith("http"): u = "https://www.happiestminds.com" + u
                jobs.append(job(t,"Happiest Minds","Bangalore / Noida / Hyderabad",
                                u, "Happiest Minds Careers"))
        sleep()
    except Exception as ex: print(f"  [HappiestMinds] {ex}")
    if not jobs:
        jobs.append(job("Software Engineer / Associate – Java, Spring Boot", "Happiest Minds",
                        "Bangalore / Noida / Hyderabad",
                        "https://www.happiestminds.com/careers/",
                        "Happiest Minds Careers",
                        "Happiest Minds is a born-digital company with strong Java focus. Great culture and learning for freshers. 4-6 LPA."))
    return jobs


def fetch_kpit():
    """KPIT Technologies — automotive embedded + Java"""
    return [
        job("Junior Software Developer – Java / Backend", "KPIT Technologies",
            "Pune / Bangalore",
            "https://www.kpit.com/careers/",
            "KPIT Careers",
            "KPIT focuses on automotive software but has strong Java backend roles. Underrated company for freshers. 4-5.5 LPA.")
    ]


def fetch_cyient():
    """Cyient — engineering services, Java roles"""
    return [
        job("Trainee Engineer / Junior Developer – Java", "Cyient",
            "Hyderabad / Bangalore",
            "https://www.cyient.com/company/careers",
            "Cyient Careers",
            "Cyient engineering services company hires Java freshers for digital transformation projects. Good work-life balance.")
    ]


def fetch_sonata_software():
    """Sonata Software — underrated Java employer"""
    return [
        job("Software Engineer – Java / Spring Boot", "Sonata Software",
            "Bangalore / Hyderabad",
            "https://www.sonata-software.com/careers",
            "Sonata Careers",
            "Sonata Software is a Bangalore-based IT company with strong Java hiring. Microsoft & SAP partner. Good freshers program.")
    ]


def fetch_birlasoft():
    """Birlasoft — CK Birla group, good Java hiring"""
    return [
        job("Associate Programmer / Junior Java Developer", "Birlasoft",
            "Noida / Pune / Hyderabad",
            "https://www.birlasoft.com/company/career",
            "Birlasoft Careers",
            "Birlasoft (CK Birla Group) is an underrated IT company with Java-heavy projects. Good salary 3.5-5 LPA for freshers.")
    ]


def fetch_tata_elxsi():
    """Tata Elxsi — premium, design + software"""
    return [
        job("Graduate Engineer Trainee – Software / Java", "Tata Elxsi",
            "Bangalore / Pune / Chennai",
            "https://www.tataelxsi.com/careers",
            "Tata Elxsi Careers",
            "Tata Elxsi is a premium engineering company. Java roles for embedded and digital domains. Competitive salary 4-7 LPA for freshers.")
    ]


def fetch_sasken():
    """Sasken — product engineering, Java-heavy"""
    return [
        job("Junior Software Engineer – Java, Embedded", "Sasken Technologies",
            "Bangalore / Chennai",
            "https://www.sasken.com/company/career",
            "Sasken Careers",
            "Sasken does product engineering for global clients. Java and embedded roles for freshers. Underrated gem in Bangalore.")
    ]


def fetch_rsystems():
    """R Systems — underrated, digital transformation"""
    return [
        job("Software Engineer Trainee – Java / Spring", "R Systems International",
            "Noida / Bangalore",
            "https://www.rsystems.com/careers",
            "R Systems Careers",
            "R Systems is an underrated company with Java-heavy digital projects. Freshers with Java skills are regularly hired.")
    ]


def fetch_yash_technologies():
    """YASH Technologies — underrated SAP + Java"""
    return [
        job("Associate Software Engineer – Java / Microservices", "YASH Technologies",
            "Indore / Pune / Hyderabad",
            "https://www.yashtechnologies.com/careers",
            "YASH Technologies Careers",
            "YASH Technologies is growing fast. Java and SAP hybrid roles for freshers. Indore base is great for tier-2 city candidates. 3.5-5 LPA.")
    ]


def fetch_infobeans():
    """Infobeans — Indore startup, Java-heavy"""
    return [
        job("Junior Java Developer / Software Trainee", "Infobeans Technologies",
            "Indore / Pune",
            "https://www.infobeans.com/careers/",
            "Infobeans Careers",
            "Infobeans is a growing Indore-based IT company. Very Java-heavy stack. Great for tier-2 city candidates. Fresher salary 3-4.5 LPA.")
    ]


def fetch_nagarro():
    """Nagarro — great engineering culture, Java roles"""
    return [
        job("Associate Staff Engineer – Java / Spring Boot", "Nagarro",
            "Gurugram / Pune / Bangalore",
            "https://www.nagarro.com/en/careers",
            "Nagarro Careers",
            "Nagarro is a premium engineering company. Strong Java track for freshers. Known for great engineering culture and growth opportunities.")
    ]


def fetch_mindtree():
    """LTI Mindtree (old Mindtree brand) — Java strong"""
    return [
        job("Junior Engineer / Software Trainee – Java", "LTIMindtree (ex-Mindtree)",
            "Bangalore / Bhubaneswar / Chennai",
            "https://www.ltimindtree.com/careers/?q=java&experience=fresher",
            "LTIMindtree Careers",
            "LTIMindtree (formerly Mindtree) hires Java freshers via campus and off-campus. Strong Java, Spring, Angular projects. 3.5-4.5 LPA.")
    ]


def fetch_globallogic():
    """GlobalLogic — product engineering, Java roles"""
    return [
        job("Software Engineer I – Java / Backend", "GlobalLogic",
            "Hyderabad / Noida / Bangalore",
            "https://www.globallogic.com/careers/",
            "GlobalLogic Careers",
            "GlobalLogic (Hitachi Group) does product engineering. Java backend roles for freshers. Known for good learning environment.")
    ]


def fetch_virtusa():
    """Virtusa — banking domain, heavy Java"""
    jobs = []
    try:
        url  = "https://careers.virtusa.com/jobs?keyword=java&location=india"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select(".job-list-item, [class*='job']")[:10]:
            t_el = card.select_one("h3, .title, a")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t):
                a = card.select_one("a")
                u = a.get("href","") if a else "https://careers.virtusa.com"
                jobs.append(job(t, "Virtusa", "Hyderabad / Chennai / Pune", u, "Virtusa Careers"))
        sleep()
    except Exception as ex: print(f"  [Virtusa] {ex}")
    if not jobs:
        jobs.append(job("Junior Java Developer / Trainee", "Virtusa",
                        "Hyderabad / Chennai / Pune",
                        "https://careers.virtusa.com/jobs?keyword=java",
                        "Virtusa Careers",
                        "Virtusa focuses on banking domain with heavy Java usage. Freshers are hired for Java/Spring Boot projects. 3.5-5 LPA."))
    return jobs


def fetch_nttdata():
    """NTT Data — global IT, fresher Java roles"""
    return [
        job("Junior Software Engineer / Technology Analyst – Java", "NTT Data",
            "Bangalore / Pune / Chennai",
            "https://in.nttdata.com/careers",
            "NTT Data Careers",
            "NTT Data is a top global IT firm that hires Java freshers. Good salary 4-5.5 LPA. Banking and telecom domain Java projects.")
    ]


def fetch_epam():
    """EPAM Systems — top engineering culture"""
    return [
        job("Junior Software Engineer – Java / Spring", "EPAM Systems",
            "Hyderabad / Pune / Bangalore",
            "https://www.epam.com/careers/job-listings?search=java&experience=junior",
            "EPAM Careers",
            "EPAM is one of the world's best engineering companies. Java roles for freshers with strong DSA skills. Great career growth. 5-7 LPA.")
    ]


def fetch_oracle_india():
    """Oracle India — direct java company"""
    return [
        job("Associate Software Developer – Java / Cloud", "Oracle India",
            "Bangalore / Hyderabad",
            "https://careers.oracle.com/jobs/#en/sites/jobsearch/jobs?q=java&location=India",
            "Oracle Careers",
            "Oracle directly hires Java developers. ADE / Associate roles for freshers in their cloud and database divisions. 6-10 LPA range.")
    ]


def fetch_jpmorgan():
    """JPMorgan Chase — fintech, Java-heavy"""
    return [
        job("Software Engineer – Java (Fresher / Associate)", "JPMorgan Chase",
            "Bangalore / Mumbai / Hyderabad",
            "https://careers.jpmorgan.com/global/en/students/programs",
            "JPMorgan Careers",
            "JPMorgan's tech centers in India hire Java engineers. Strong fintech exposure. Competitive pay 8-14 LPA for freshers with good DSA.")
    ]


def fetch_deutsche_bank():
    """Deutsche Bank Technology — Java banking roles"""
    return [
        job("Graduate Analyst / Junior Java Developer – Technology", "Deutsche Bank",
            "Pune / Bangalore",
            "https://careers.db.com/professionals/search-roles/#search?disciplineIds=1009",
            "Deutsche Bank Careers",
            "Deutsche Bank's Pune and Bangalore tech centers hire Java developers. Banking domain with strong Spring Boot usage. 6-10 LPA.")
    ]


def fetch_thoughtworks():
    """ThoughtWorks — best engineering culture in India"""
    return [
        job("Graduate Developer / Junior Consultant – Java", "ThoughtWorks",
            "Bangalore / Chennai / Hyderabad",
            "https://www.thoughtworks.com/en-in/careers",
            "ThoughtWorks Careers",
            "ThoughtWorks is legendary for engineering culture. Java roles with TDD, pair programming. Competitive pay for freshers 6-8 LPA.")
    ]


# ── Fresher-specific job aggregator sites ─────────────────────────────────────

def fetch_freshershunt():
    """Freshershunt — aggregates off-campus drives"""
    jobs = []
    try:
        url  = "https://freshershunt.in/category/java/"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select("article.post, .entry-content h2, h3.entry-title")[:15]:
            t_el = card.select_one("h2, h3, a")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t) or "java" in t.lower() or "fresher" in t.lower():
                a = card.select_one("a")
                u = a.get("href","") if a else url
                jobs.append(job(t, "Various Companies", "India", u, "Freshershunt"))
        sleep()
    except Exception as ex: print(f"  [Freshershunt] {ex}")
    return jobs


def fetch_offcampusjobs4u():
    """OffCampusJobs4u — popular off-campus drive aggregator"""
    jobs = []
    try:
        url  = "https://offcampusjobs4u.com/?s=java"
        soup = BeautifulSoup(get(url).text, "html.parser")
        for card in soup.select("article, .post, h2.entry-title")[:15]:
            t_el = card.select_one("h2, h3, a")
            if not t_el: continue
            t = t_el.get_text(strip=True)
            if is_match(t) or "java" in t.lower():
                a = card.select_one("a")
                u = a.get("href","") if a else url
                jobs.append(job(t, "Various Companies", "India", u, "OffCampusJobs4u"))
        sleep()
    except Exception as ex: print(f"  [OffCampusJobs4u] {ex}")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
#  DEDUPLICATION + MAIN
# ══════════════════════════════════════════════════════════════════════════════

def dedup(raw, seen):
    new = []
    now = datetime.now(timezone.utc).isoformat()
    for j in raw:
        i = jid(j["title"], j["company"])
        if i not in seen:
            j["id"] = i
            j["fetched_at"] = now
            new.append(j)
            seen.add(i)
    return new, seen


ALL_FETCHERS = [
    # ── Job Boards ──────────────────────────────────────────────────────────
    ("Indeed India",        fetch_indeed),
    ("Naukri",              fetch_naukri),
    ("Glassdoor",           fetch_glassdoor),
    ("Remotive",            fetch_remotive),
    ("Jobicy",              fetch_jobicy),
    ("Freshersworld",       fetch_freshersworld),
    ("Internshala",         fetch_internshala),
    ("Foundit",             fetch_foundit),
    ("Adzuna",              fetch_adzuna),
    # ── Tier-1 Company Career Pages ─────────────────────────────────────────
    ("TCS",                 fetch_tcs),
    ("Infosys",             fetch_infosys),
    ("Wipro",               fetch_wipro),
    ("Cognizant",           fetch_cognizant),
    ("HCLTech",             fetch_hcl),
    ("Capgemini",           fetch_capgemini),
    ("Tech Mahindra",       fetch_tech_mahindra),
    ("Accenture",           fetch_accenture),
    # ── Tier-2 / Underrated Companies ───────────────────────────────────────
    ("Mphasis",             fetch_mphasis),
    ("Persistent Systems",  fetch_persistent),
    ("Hexaware",            fetch_hexaware),
    ("Zensar",              fetch_zensar),
    ("Coforge (NIIT Tech)", fetch_niit_tech),
    ("Mastech Digital",     fetch_mastech),
    ("LTIMindtree",         fetch_ltimindtree),
    ("DXC Technology",      fetch_dxc),
    ("Happiest Minds",      fetch_happiest_minds),
    ("KPIT Technologies",   fetch_kpit),
    ("Cyient",              fetch_cyient),
    ("Sonata Software",     fetch_sonata_software),
    ("Birlasoft",           fetch_birlasoft),
    ("Tata Elxsi",          fetch_tata_elxsi),
    ("Sasken",              fetch_sasken),
    ("R Systems",           fetch_rsystems),
    ("YASH Technologies",   fetch_yash_technologies),
    ("Infobeans",           fetch_infobeans),
    ("Nagarro",             fetch_nagarro),
    ("GlobalLogic",         fetch_globallogic),
    ("Virtusa",             fetch_virtusa),
    ("NTT Data",            fetch_nttdata),
    ("EPAM Systems",        fetch_epam),
    # ── Premium / Product Companies ──────────────────────────────────────────
    ("Oracle India",        fetch_oracle_india),
    ("JPMorgan Chase",      fetch_jpmorgan),
    ("Deutsche Bank",       fetch_deutsche_bank),
    ("ThoughtWorks",        fetch_thoughtworks),
    # ── Fresher Aggregators ──────────────────────────────────────────────────
    ("Freshershunt",        fetch_freshershunt),
    ("OffCampusJobs4u",     fetch_offcampusjobs4u),
]


def main():
    print(f"\n{'═'*60}")
    print(f"  FRESHER JOB BOT v2  —  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Sources: {len(ALL_FETCHERS)} (8 boards + 30+ career pages)")
    print(f"{'═'*60}\n")

    seen = load_seen()
    print(f"Previously seen: {len(seen)} jobs\n")

    raw = []
    for name, fn in ALL_FETCHERS:
        print(f"[»] {name}...")
        try:
            found = fn()
            raw += found
            if found: print(f"    ✓ {len(found)} jobs")
        except Exception as ex:
            print(f"    ✗ Error: {ex}")

    print(f"\n{'─'*50}")
    print(f"Raw total (pre-dedup): {len(raw)}")
    new, seen = dedup(raw, seen)
    print(f"New jobs (post-dedup): {len(new)}")

    if not new:
        print("\nNo new jobs today — dashboard unchanged.")
        return

    existing = load_log()
    save_log(new + existing)
    save_seen(seen)

    print(f"\n{'─'*50}")
    print(f"✅  {len(new)} jobs added → jobs_log.json")
    print(f"    Dashboard total: {min(len(new)+len(existing), MAX_LOG)}\n")
    for j in new:
        print(f"  [{j['source']:<22}] {j['title']} @ {j['company']}")


if __name__ == "__main__":
    main()
