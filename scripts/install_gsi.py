"""Automatic Dota 2 Game State Integration (GSI) installer script."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

def get_steam_install_path() -> Path | None:
    """Find main Steam installation path from Windows registry or common locations."""
    if sys.platform == "win32":
        import winreg
        for key_path in [r"SOFTWARE\Valve\Steam", r"SOFTWARE\WOW6432Node\Valve\Steam"]:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    val, _ = winreg.QueryValueEx(key, "InstallPath")
                    if val and Path(val).exists():
                        return Path(val)
            except OSError:
                pass
        # Common fallbacks
        for p in [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]:
            if p.exists():
                return p
    else:
        for p in [Path.home() / ".local/share/Steam", Path.home() / ".steam/steam"]:
            if p.exists():
                return p
    return None

def find_all_steam_libraries() -> list[Path]:
    """Parse libraryfolders.vdf to locate all Steam library directories across all drives."""
    libraries: list[Path] = []
    steam_path = get_steam_install_path()
    if not steam_path:
        return libraries

    libraries.append(steam_path)
    vdf_file = steam_path / "steamapps" / "libraryfolders.vdf"
    if vdf_file.exists():
        try:
            content = vdf_file.read_text(encoding="utf-8", errors="ignore")
            # Look for "path" "D:\\SteamLibrary" entries
            matches = re.findall(r'"path"\s+"([^"]+)"', content)
            for m in matches:
                clean_path = Path(m.replace(r"\\", "\\"))
                if clean_path.exists() and clean_path not in libraries:
                    libraries.append(clean_path)
        except Exception as e:
            print(f"[!] Warning reading libraryfolders.vdf: {e}")

    # Also add standard drive roots as fallback
    for drive in ["C", "D", "E", "F", "G"]:
        p = Path(f"{drive}:\\SteamLibrary")
        if p.exists() and p not in libraries:
            libraries.append(p)

    return libraries

def find_dota2_cfg_dir() -> Path | None:
    """Find the exact Dota 2 cfg directory across all Steam library paths."""
    libraries = find_all_steam_libraries()
    for lib in libraries:
        candidate = lib / "steamapps" / "common" / "dota 2 beta" / "game" / "dota" / "cfg"
        if candidate.exists():
            return candidate
    return None

def install() -> bool:
    root = Path(__file__).resolve().parent.parent
    source_cfg = root / "data" / "gsi" / "gamestate_integration_dotablitz.cfg"
    
    if not source_cfg.exists():
        print(f"[!] Source config not found at: {source_cfg}")
        return False

    cfg_dir = find_dota2_cfg_dir()
    if not cfg_dir:
        print("[!] Could not automatically locate your Dota 2 installation.")
        print(f"Please manually copy '{source_cfg}' into:")
        print("    <Your Steam Folder>\\steamapps\\common\\dota 2 beta\\game\\dota\\cfg\\gamestate_integration\\")
        return False

    target_dir = cfg_dir / "gamestate_integration"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "gamestate_integration_dotablitz.cfg"

    try:
        shutil.copy2(source_cfg, target_file)
        print(f"[OK] Successfully installed Dota 2 GSI configuration:")
        print(f"    Target: {target_file}")
        return True
    except Exception as exc:
        print(f"[!] Failed to copy file: {exc}")
        return False

if __name__ == "__main__":
    install()
