"""Dotabuff scraper – extracts hero builds, items, and winrate data."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("dotablitz.dotabuff")

BASE_URL = "https://www.dotabuff.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class DotabuffScraper:
    """Scrape hero data from dotabuff.com (best-effort, gracefully degrades)."""

    async def _fetch(self, url: str) -> BeautifulSoup | None:
        """Fetch a page and return parsed HTML, or None on failure."""
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url, headers=HEADERS)
                if resp.status_code != 200:
                    logger.warning("Dotabuff returned %s for %s", resp.status_code, url)
                    return None
                return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.error("Dotabuff fetch error for %s: %s", url, exc)
            return None

    # ── public methods ───────────────────────────────────────────────

    async def get_hero_builds(self, hero_slug: str) -> list[dict[str, Any]]:
        """
        Scrape the /heroes/<slug>/builds page.

        Returns list of builds, each with item list, skill order, winrate, matches.
        ``hero_slug`` should be the URL-friendly hero name, e.g. "anti-mage".
        """
        soup = await self._fetch(f"{BASE_URL}/heroes/{hero_slug}/builds")
        if soup is None:
            return []

        builds: list[dict] = []
        build_tables = soup.select("table.sortable tbody tr")

        for row in build_tables[:10]:  # top 10 builds
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # Extract items from the build row
            items: list[str] = []
            item_imgs = row.select("img[src*='items']")
            for img in item_imgs:
                src = img.get("src", "")
                alt = img.get("alt", "")
                if alt:
                    items.append(alt.lower().replace(" ", "_").replace("'", ""))

            # Extract winrate
            winrate = 0.0
            matches = 0
            for cell in cells:
                text = cell.get_text(strip=True)
                if "%" in text:
                    try:
                        winrate = float(text.replace("%", "").replace(",", "."))
                    except ValueError:
                        pass
                elif text.replace(",", "").isdigit():
                    matches = int(text.replace(",", ""))

            if items:
                builds.append({
                    "items": items,
                    "winrate": winrate,
                    "matches": matches,
                    "source": "dotabuff",
                })

        logger.info("Dotabuff: scraped %d builds for %s", len(builds), hero_slug)
        return builds

    async def get_hero_items(self, hero_slug: str) -> dict[str, list[dict]]:
        """
        Scrape /heroes/<slug>/items – returns items grouped by phase.

        Returns dict with keys 'early', 'core', 'late', each a list of
        {name, winrate, matches} dicts.
        """
        soup = await self._fetch(f"{BASE_URL}/heroes/{hero_slug}/items")
        if soup is None:
            return {"early": [], "core": [], "late": []}

        result: dict[str, list[dict]] = {"early": [], "core": [], "late": []}

        # Dotabuff groups items under header rows or sections
        tables = soup.select("table")
        phase_keywords = {
            "early": ["starting", "early"],
            "core": ["core", "mid"],
            "late": ["late", "luxury", "extension"],
        }

        for table in tables:
            # Try to determine which phase this table belongs to
            prev_header = table.find_previous(["h2", "h3", "h4"])
            header_text = prev_header.get_text(strip=True).lower() if prev_header else ""

            phase = "core"  # default
            for p, keywords in phase_keywords.items():
                if any(kw in header_text for kw in keywords):
                    phase = p
                    break

            rows = table.select("tbody tr")
            for row in rows[:10]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                name_el = row.select_one("td.cell-xlarge")
                name = name_el.get_text(strip=True) if name_el else ""
                if not name:
                    # fallback: first cell
                    name = cells[0].get_text(strip=True)

                winrate = 0.0
                matches = 0
                for cell in cells[1:]:
                    text = cell.get_text(strip=True)
                    if "%" in text:
                        try:
                            winrate = float(text.replace("%", "").replace(",", "."))
                        except ValueError:
                            pass
                    elif text.replace(",", "").isdigit():
                        matches = int(text.replace(",", ""))

                if name:
                    result[phase].append({
                        "name": name.lower().replace(" ", "_").replace("'", ""),
                        "display_name": name,
                        "winrate": winrate,
                        "matches": matches,
                    })

        return result

    async def get_hero_winrate(self, hero_slug: str) -> dict[str, Any]:
        """Scrape main hero page for overall winrate and pick rate."""
        soup = await self._fetch(f"{BASE_URL}/heroes/{hero_slug}")
        if soup is None:
            return {"winrate": 0.0, "pick_rate": 0.0}

        winrate = 0.0
        pick_rate = 0.0

        # Look for winrate in the header stats section
        header = soup.select_one("div.header-content-secondary")
        if header:
            spans = header.find_all("span")
            for span in spans:
                text = span.get_text(strip=True)
                if "%" in text:
                    try:
                        val = float(text.replace("%", "").replace(",", "."))
                        if winrate == 0.0:
                            winrate = val
                        else:
                            pick_rate = val
                    except ValueError:
                        pass

        return {"winrate": winrate, "pick_rate": pick_rate}

    async def get_hero_skill_order(self, hero_slug: str) -> list[int]:
        """
        Scrape skill build order from Dotabuff builds page.

        Returns a list of 25 ints (0=Q, 1=W, 2=E, 3=R).
        """
        soup = await self._fetch(f"{BASE_URL}/heroes/{hero_slug}/builds")
        if soup is None:
            return []

        # Look for the most popular skill build (first one on page)
        skill_tables = soup.select("div.skill-build, table.skill-builds")
        if not skill_tables:
            return []

        order: list[int] = []
        # Parse skill order from highlighted cells
        table = skill_tables[0]
        rows = table.find_all("tr")
        if len(rows) >= 4:
            # Each row represents a skill (Q, W, E, R)
            level_skills: dict[int, int] = {}
            for skill_idx, row in enumerate(rows[:4]):
                cells = row.find_all("td")
                for level, cell in enumerate(cells):
                    classes = cell.get("class", [])
                    if any("leveled" in c or "active" in c or "selected" in c for c in classes):
                        level_skills[level] = skill_idx

            for lvl in sorted(level_skills.keys()):
                order.append(level_skills[lvl])

        return order[:25]


def hero_name_to_slug(name: str) -> str:
    """Convert hero internal name (e.g. 'phantom_assassin') to Dotabuff URL slug ('phantom-assassin')."""
    return name.replace("_", "-").lower()
