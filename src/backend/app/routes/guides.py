"""Guide generation and export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

from ..config import settings
from ..database import async_session
from ..models.database_models import Hero, HeroBuild
from ..services.guide_generator import guide_generator

router = APIRouter(prefix="/guides", tags=["guides"])


@router.post("/generate/{build_id}")
async def generate_guide(build_id: int):
    """Generate a Steam Community Guide from a stored build."""
    async with async_session() as session:
        build = await session.get(HeroBuild, build_id)
        if not build:
            raise HTTPException(404, "Build not found")
        hero = await session.get(Hero, build.hero_id)
        if not hero:
            raise HTTPException(404, "Hero not found")

    text = guide_generator.generate_guide_text(build, hero)
    html = guide_generator.generate_guide_html(build, hero)
    filename = f"{hero.name}_{build.build_type}_guide.txt"

    return {
        "title": f"{hero.localized_name} – {build.build_type.title()} Build",
        "content": text,
        "html_preview": html,
        "filename": filename,
    }


@router.post("/install-in-game/{build_id}")
async def install_in_game(build_id: int):
    """Directly install the build into the local Dota 2 client shop directory."""
    async with async_session() as session:
        build = await session.get(HeroBuild, build_id)
        if not build:
            raise HTTPException(404, "Build not found")
        hero = await session.get(Hero, build.hero_id)
        if not hero:
            raise HTTPException(404, "Hero not found")

    target = guide_generator.install_to_dota_game(build, hero)
    if not target:
        raise HTTPException(500, "Could not locate Dota 2 itembuilds directory.")

    return {
        "status": "success",
        "message": f"Guia de {hero.localized_name} instalado com sucesso diretamente no Dota 2!",
        "file": str(target),
        "hero": hero.localized_name,
    }


@router.get("/export/{build_id}")
async def export_guide(build_id: int):
    """Download the guide as a plain-text file."""
    async with async_session() as session:
        build = await session.get(HeroBuild, build_id)
        if not build:
            raise HTTPException(404, "Build not found")
        hero = await session.get(Hero, build.hero_id)
        if not hero:
            raise HTTPException(404, "Hero not found")

    text = guide_generator.generate_guide_text(build, hero)
    filename = f"{hero.name}_{build.build_type}_guide.txt"

    # Also save to disk
    filepath = settings.DATA_DIR / "guides" / filename
    guide_generator.export_to_file(build, hero, filepath)

    return PlainTextResponse(
        content=text,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/preview/{build_id}", response_class=HTMLResponse)
async def preview_guide(build_id: int):
    """Preview the guide as rendered HTML."""
    async with async_session() as session:
        build = await session.get(HeroBuild, build_id)
        if not build:
            raise HTTPException(404, "Build not found")
        hero = await session.get(Hero, build.hero_id)
        if not hero:
            raise HTTPException(404, "Hero not found")

    html = guide_generator.generate_guide_html(build, hero)

    # Wrap in a simple dark-themed HTML page
    page = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{hero.localized_name} – DotaBlitz Guide</title>
<style>
    body {{ background: #0a0e14; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; padding: 24px; max-width: 800px; margin: 0 auto; }}
    h1 {{ color: #00d4aa; }}
    h2 {{ color: #4fc3f7; border-bottom: 1px solid #1a1f2e; padding-bottom: 6px; }}
    table {{ border-collapse: collapse; }}
    td, th {{ padding: 3px 6px; }}
    img {{ vertical-align: middle; }}
    hr {{ border-color: #1a1f2e; }}
</style>
</head><body>
{html}
</body></html>"""
    return HTMLResponse(content=page)
