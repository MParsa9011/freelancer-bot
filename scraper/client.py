import asyncio
import logging
import re
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from scraper.parser import Project, _clean, parse_budget, parse_number, parse_float

logger = logging.getLogger(__name__)

BASE_URL = "https://www.freelancer.com"

_playwright = None
_browser: Browser | None = None


async def _get_browser() -> Browser:
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
    return _browser


async def _new_context() -> BrowserContext:
    browser = await _get_browser()
    ctx = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
    )
    await ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return ctx


async def _wait_and_get(page: Page, selector: str, timeout: int = 15000) -> str:
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        el = page.locator(selector).first
        return await el.inner_text()
    except Exception:
        return ""


async def get_projects(slug: str, max_projects: int = 20) -> list[Project]:
    url = f"{BASE_URL}/jobs/{slug}/"
    ctx = await _new_context()
    try:
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Try to extract from Freelancer's internal Angular state first
        projects = await _extract_from_angular_state(page, slug)
        if projects:
            return projects[:max_projects]

        # Fallback: DOM scraping of project cards
        projects = await _extract_from_dom(page, slug)
        return projects[:max_projects]
    except Exception as e:
        logger.error("Error fetching projects for slug %s: %s", slug, e)
        return []
    finally:
        await ctx.close()


async def _extract_from_angular_state(page: Page, slug: str) -> list[Project]:
    """Try to pull project data from Freelancer's embedded JS state."""
    try:
        data = await page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d && (d.projects || d.searchResults)) return d;
                } catch {}
            }
            // Try window state objects
            for (const key of ['__INITIAL_STATE__', 'flnPageData', 'initialData']) {
                if (window[key]) return window[key];
            }
            return null;
        }""")
        if not data:
            return []

        raw_projects = (
            data.get("projects")
            or data.get("searchResults")
            or data.get("result", {}).get("projects")
            or []
        )
        if not isinstance(raw_projects, list):
            return []

        result = []
        for p in raw_projects:
            try:
                pid = str(p.get("id", ""))
                title = p.get("title", "")
                seo_url = p.get("seo_url", "")
                url = f"{BASE_URL}/projects/{seo_url}/{pid}/" if seo_url else f"{BASE_URL}/projects/{pid}/"
                budget = p.get("budget", {})
                b_min = budget.get("minimum")
                b_max = budget.get("maximum")
                bid_stats = p.get("bid_stats", {})
                bid_count = bid_stats.get("bid_count", 0)
                avg_bid = bid_stats.get("bid_avg")
                description = p.get("description", "")
                if pid and title:
                    result.append(Project(
                        project_id=pid,
                        title=_clean(title),
                        url=url,
                        budget_min=b_min,
                        budget_max=b_max,
                        bid_count=bid_count,
                        avg_bid=avg_bid,
                        description=_clean(description),
                    ))
            except Exception:
                continue
        return result
    except Exception:
        return []


async def _extract_from_dom(page: Page, slug: str) -> list[Project]:
    """Fallback: scrape project cards from rendered DOM."""
    result = []
    try:
        # Freelancer renders project cards with Angular — wait for links
        await page.wait_for_selector("a[href*='/projects/']", timeout=15000)
    except Exception:
        logger.warning("No project links found for slug: %s", slug)
        return []

    try:
        cards_html = await page.evaluate("""() => {
            // Collect all visible project card-like containers
            const links = [...document.querySelectorAll('a[href*="/projects/"]')];
            const seen = new Set();
            const cards = [];
            for (const a of links) {
                const href = a.getAttribute('href');
                const m = href.match(/\\/projects\\/[^/]+\\/(\\d+)/);
                if (!m) continue;
                const pid = m[1];
                if (seen.has(pid)) continue;
                seen.add(pid);

                // Walk up to find the card container
                let el = a;
                for (let i = 0; i < 6; i++) {
                    el = el.parentElement;
                    if (!el) break;
                }
                const container = el || a.parentElement;

                cards.push({
                    id: pid,
                    title: a.innerText.trim(),
                    href: href,
                    container_text: container ? container.innerText : ''
                });
            }
            return cards;
        }""")

        for card in cards_html:
            pid = card.get("id", "")
            title = _clean(card.get("title", ""))
            href = card.get("href", "")
            container_text = card.get("container_text", "")

            if not pid or not title or len(title) < 5:
                continue

            url = href if href.startswith("http") else BASE_URL + href

            # Extract budget from container text
            budget_match = re.search(
                r"\$\s*([\d,]+)\s*[-–]\s*\$\s*([\d,]+)", container_text
            )
            b_min, b_max = None, None
            if budget_match:
                b_min = float(budget_match.group(1).replace(",", ""))
                b_max = float(budget_match.group(2).replace(",", ""))
            else:
                single = re.search(r"\$\s*([\d,]+)", container_text)
                if single:
                    b_min = b_max = float(single.group(1).replace(",", ""))

            # Extract bid count
            bids_match = re.search(r"(\d+)\s*bids?", container_text, re.IGNORECASE)
            bid_count = int(bids_match.group(1)) if bids_match else 0

            # Short description from container text (exclude title and numbers)
            lines = [ln.strip() for ln in container_text.split("\n") if ln.strip()]
            desc_lines = [
                ln for ln in lines
                if ln != title and not re.fullmatch(r"[\d\s$,.\-–]+", ln)
            ]
            description = " ".join(desc_lines[:3])

            result.append(Project(
                project_id=pid,
                title=title,
                url=url,
                budget_min=b_min,
                budget_max=b_max,
                bid_count=bid_count,
                avg_bid=None,
                description=_clean(description),
            ))
    except Exception as e:
        logger.error("DOM extraction error: %s", e)

    return result


async def get_project_detail(project_url: str) -> dict:
    """Fetch full description and avg_bid from a project detail page."""
    ctx = await _new_context()
    try:
        page = await ctx.new_page()
        await page.goto(project_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        detail = await page.evaluate("""() => {
            // Try Angular state / JSON scripts first
            const scripts = document.querySelectorAll('script[type="application/json"]');
            for (const s of scripts) {
                try {
                    const d = JSON.parse(s.textContent);
                    if (d && d.description) return d;
                    if (d && d.project && d.project.description)
                        return d.project;
                } catch {}
            }
            return null;
        }""")

        if detail:
            bid_stats = detail.get("bid_stats", {})
            return {
                "description": _clean(detail.get("description", "")),
                "avg_bid": bid_stats.get("bid_avg"),
                "bid_count": bid_stats.get("bid_count"),
            }

        # DOM fallback
        desc = ""
        avg_bid = None

        # Description — try common selectors
        for sel in [
            "[class*='description']",
            "[class*='NativeElement']",
            ".project-description",
            "fl-text p",
            "p",
        ]:
            try:
                await page.wait_for_selector(sel, timeout=5000)
                texts = await page.locator(sel).all_inner_texts()
                long_texts = [t.strip() for t in texts if len(t.strip()) > 80]
                if long_texts:
                    desc = _clean(" ".join(long_texts[:5]))
                    break
            except Exception:
                continue

        # Average bid — look for currency amounts near "average" or "avg"
        try:
            page_text = await page.inner_text("body")
            avg_match = re.search(
                r"(?:avg(?:erage)?\s*bid|average)[^\d$]*\$?\s*([\d,]+(?:\.\d+)?)",
                page_text,
                re.IGNORECASE,
            )
            if avg_match:
                avg_bid = float(avg_match.group(1).replace(",", ""))
        except Exception:
            pass

        return {"description": desc, "avg_bid": avg_bid, "bid_count": None}

    except Exception as e:
        logger.error("Error fetching project detail %s: %s", project_url, e)
        return {"description": "", "avg_bid": None, "bid_count": None}
    finally:
        await ctx.close()


async def close_browser() -> None:
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
