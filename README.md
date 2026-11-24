# dubass83.xyz — CV site

One-page bilingual (EN/UK) CV, plus downloadable **PDF**, **DOCX** and **Markdown** versions,
all generated from a single file: [`cv.yaml`](cv.yaml).

```
cv.yaml                  ← all content: profile, jobs, skills, certs, courses, UI strings
templates/index.html.j2  ← web page (also printed to PDF)
templates/cv.md.j2       ← Markdown CV (converted to DOCX by pandoc)
static/                  ← CSS, photo, certificate images, CNAME, favicon
build.py                 ← renders everything into dist/
.github/workflows/       ← builds on every push to `src`, deploys to GitHub Pages
```

## Build locally

Requirements: Python 3.9+, [pandoc](https://pandoc.org/installing.html) (DOCX), Google Chrome or Chromium (PDF).

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python build.py --serve      # http://localhost:8000
```

Flags: `--no-pdf` skips Chrome, `--strict` fails when pandoc or Chrome is missing (CI uses it).
Set `CHROME=/path/to/chrome` if the browser lives somewhere unusual.

Output:

```
dist/index.html                      English page
dist/uk/index.html                   Ukrainian page
dist/cv/maksym-sych-cv-{en,uk}.pdf
dist/cv/maksym-sych-cv-{en,uk}.docx
dist/cv/maksym-sych-cv-{en,uk}.md
```

To add a job, certification or badge, see [DEPLOY.md](DEPLOY.md).
