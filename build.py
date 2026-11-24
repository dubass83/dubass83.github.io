#!/usr/bin/env python3
"""Build the CV site and downloadable CV files (MD, DOCX, PDF) from cv.yaml.

    python build.py            # build everything into dist/
    python build.py --no-pdf   # skip the PDF (no Chrome needed)
    python build.py --strict   # fail if pandoc or Chrome is missing (used in CI)
    python build.py --serve    # build, then serve dist/ on http://localhost:8000
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import hashlib
import http.server
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, ChainableUndefined

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
LANGS = ["en", "uk"]  # first one is the default and lives at the site root
CV_BASENAME = "maksym-sych-cv"

CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


# ---------------------------------------------------------------- data helpers

def tr(value, lang: str):
    """Pick the `lang` variant of a translatable value (falls back to English)."""
    if isinstance(value, dict) and ("en" in value or lang in value):
        return value.get(lang, value.get("en"))
    return value


def parse_ym(value) -> tuple[int, int | None] | None:
    """'2021-05' -> (2021, 5); 2006 -> (2006, None); None -> None."""
    if value in (None, ""):
        return None
    s = str(value)
    if "-" in s:
        y, m = s.split("-")[:2]
        return int(y), int(m)
    return int(s), None


def fmt_date(value, lang: str, ui: dict) -> str:
    parsed = parse_ym(value)
    if parsed is None:
        return ui["present"]
    year, month = parsed
    return f"{ui['months'][month - 1]} {year}" if month else str(year)


def is_expired(value) -> bool:
    parsed = parse_ym(value)
    if not parsed:
        return False
    year, month = parsed
    today = dt.date.today()
    return (year, month or 12) < (today.year, today.month)


def validate(cv: dict) -> None:
    errors = []
    for section in ("certifications", "training"):
        for i, item in enumerate(cv.get(section, [])):
            for key in ("name", "issuer", "date"):
                if not item.get(key):
                    errors.append(f"{section}[{i}] is missing '{key}'")
            image = item.get("image")
            if image and not (ROOT / image).is_file():
                errors.append(f"{section}[{i}] image not found: {image}")
    for i, job in enumerate(cv.get("experience", [])):
        for key in ("role", "company", "start"):
            if not job.get(key):
                errors.append(f"experience[{i}] is missing '{key}'")
    if errors:
        sys.exit("cv.yaml has problems:\n  - " + "\n  - ".join(errors))


def sort_by_date(items: list[dict]) -> list[dict]:
    """Newest first; anything already expired goes to the end."""
    return sorted(
        items,
        key=lambda x: (not is_expired(x.get("expires")), parse_ym(x.get("date")) or (0, 0)),
        reverse=True,
    )


# ---------------------------------------------------------------- rendering

def make_env(lang: str, ui: dict) -> Environment:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=ChainableUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=lambda name: bool(name) and name.endswith(".html.j2"),
    )
    env.filters["t"] = lambda v: tr(v, lang)
    env.filters["date"] = lambda v: fmt_date(v, lang, ui)
    env.filters["expired"] = is_expired
    return env


def render_lang(cv: dict, lang: str, chrome: str | None, pandoc: str | None) -> None:
    ui = cv["ui"][lang]
    out_dir = DIST if lang == LANGS[0] else DIST / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    root = "" if lang == LANGS[0] else "../"

    files_dir = DIST / "cv"
    files_dir.mkdir(exist_ok=True)
    base = f"{CV_BASENAME}-{lang}"
    downloads = [("PDF", f"{root}cv/{base}.pdf"), ("DOCX", f"{root}cv/{base}.docx"), ("Markdown", f"{root}cv/{base}.md")]
    if not chrome:
        downloads = [d for d in downloads if d[0] != "PDF"]
    if not pandoc:
        downloads = [d for d in downloads if d[0] != "DOCX"]

    ctx = dict(
        cv=cv,
        lang=lang,
        ui=ui,
        root=root,
        langs=[(code, cv["ui"][code]["lang_name"], "" if code == LANGS[0] else f"{code}/") for code in LANGS],
        certifications=sort_by_date(cv.get("certifications", [])),
        training=sort_by_date(cv.get("training", [])),
        downloads=downloads,
        updated=dt.date.today().isoformat(),
        css_v=hashlib.sha256((ROOT / "static" / "style.css").read_bytes()).hexdigest()[:10],
    )
    env = make_env(lang, ui)

    page = out_dir / "index.html"
    page.write_text(env.get_template("index.html.j2").render(**ctx), encoding="utf-8")
    log(f"{page.relative_to(ROOT)}")

    md = files_dir / f"{base}.md"
    md.write_text(env.get_template("cv.md.j2").render(**ctx), encoding="utf-8")
    log(f"{md.relative_to(ROOT)}")

    if pandoc:
        docx = files_dir / f"{base}.docx"
        subprocess.run([pandoc, str(md), "-f", "markdown", "-M", f"lang={lang}", "-o", str(docx)], check=True)
        log(f"{docx.relative_to(ROOT)}")

    if chrome:
        pdf = files_dir / f"{base}.pdf"
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
             "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000",
             f"--print-to-pdf={pdf}", page.as_uri()],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        log(f"{pdf.relative_to(ROOT)}")


def find_tool(candidates: list[str]) -> str | None:
    for c in candidates:
        if not c:
            continue
        path = c if os.path.isabs(c) and os.access(c, os.X_OK) else shutil.which(c)
        if path:
            return path
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-pdf", action="store_true", help="skip PDF generation")
    ap.add_argument("--strict", action="store_true", help="fail if pandoc/Chrome are missing")
    ap.add_argument("--serve", action="store_true", help="serve dist/ on :8000 after building")
    args = ap.parse_args()

    cv = yaml.safe_load((ROOT / "cv.yaml").read_text(encoding="utf-8"))
    validate(cv)

    pandoc = find_tool(["pandoc"])
    chrome = None if args.no_pdf else find_tool(CHROME_CANDIDATES)
    missing = [n for n, p in (("pandoc", pandoc), ("Chrome", chrome)) if not p and not (n == "Chrome" and args.no_pdf)]
    if missing:
        msg = f"not found: {', '.join(missing)} — related downloads will be skipped"
        if args.strict:
            sys.exit(f"[build] {msg}")
        log(f"WARNING {msg}")

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST / "static")
    for name in ("CNAME", "favicon.ico"):
        shutil.move(str(DIST / "static" / name), DIST / name)
    (DIST / ".nojekyll").touch()

    for lang in LANGS:
        render_lang(cv, lang, chrome, pandoc)
    log("done")

    if args.serve:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
        log("serving http://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()


if __name__ == "__main__":
    main()
