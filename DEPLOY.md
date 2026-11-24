# Updating and deploying the CV

Everything is driven by `cv.yaml`. Push to the `src` branch → GitHub Actions rebuilds the
site and the PDF/DOCX/MD files → GitHub Pages serves them at https://dubass83.xyz.
Nothing has to be built or deployed from a laptop.

## Routine updates

### Add a certification

1. Save the certificate image (JPG/PNG) and make an optimized copy plus a thumbnail:

   ```sh
   # macOS (sips is built in). On Linux use ImageMagick: magick in.png -resize 1600x out.jpg
   sips -s format jpeg -s formatOptions 80 -Z 1600 ~/Downloads/new-cert.png --out static/certs/cka-2026.jpg
   sips -s format jpeg -s formatOptions 75 -Z 640  ~/Downloads/new-cert.png --out static/certs/cka-2026.thumb.jpg
   ```

   The page expects `<name>.jpg` and `<name>.thumb.jpg` side by side.

2. Add an entry to `certifications:` (proctored exams) or `training:` (courses) in `cv.yaml`:

   ```yaml
   - name: Certified Kubernetes Administrator (CKA)
     issuer: CNCF / The Linux Foundation
     date: 2026-03          # YYYY-MM
     expires: 2028-03       # optional; expired certs are greyed out and listed last
     id: LF-xxxxxxxxxx      # optional
     verify: https://www.credly.com/badges/<id>   # optional
     image: static/certs/cka-2026.jpg            # optional
   ```

   Order doesn't matter; the build sorts newest first.

3. Commit and push (see "Publish" below).

### Add a badge (shields.io style)

```yaml
badges:
  - name: SadServers Master
    url: https://sadservers.com
    image: https://img.shields.io/badge/SadServers-Master-FF6D00?style=for-the-badge&labelColor=FFC400&logo=kubernetes&logoColor=1A237E&logoSize=auto
```

### Add or close a job

Put the newest job **first** under `experience:`. Leave `end:` empty for the current one.
When you leave, set `end: YYYY-MM`.

```yaml
- role: { en: Senior DevOps Engineer, uk: Старший DevOps-інженер }
  company: Example Corp
  location: { en: "Remote", uk: "Віддалено" }
  start: 2024-02
  end:
  highlights:
    - en: Cut EKS spend 35% with Karpenter and spot node pools.
      uk: Зменшив витрати на EKS на 35% завдяки Karpenter і spot-нодам.
```

Quote any value that contains a comma inside `{ ... }` (for example `{ en: "Kyiv, Ukraine" }`).
Any text field can be a plain string (same in both languages) or `{ en: ..., uk: ... }`.

## Publish

```sh
python build.py --serve          # optional: check it locally first
git add cv.yaml static/
git commit -m "Add CKA 2026"
git push origin src              # CI builds and deploys in ~1–2 min
```

Prefer a PR for bigger edits: open a PR into `src` and CI builds it without deploying.
The built PDF/DOCX/MD are attached to the run as the `cv-files` artifact, so you can review them before merging.

`build.py` checks `cv.yaml` before rendering. A missing `name`/`issuer`/`date` or a wrong
image path fails the build, so a typo never reaches the live site.

## One-time GitHub setup (needed before the first Actions deploy)

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
   Keep the custom domain `dubass83.xyz` and "Enforce HTTPS" as they are.
2. **Settings → Environments → github-pages → Deployment branches**: allow `src`.
   (By default only the default branch, `master`, may deploy.)
3. Recommended: **Settings → General → Default branch → `src`**.
   After the first successful deploy, the old `master` branch (Nikola output) is no
   longer used. It can be kept for history or deleted.

## Rollback

Every deploy comes from a commit on `src`. To roll back, `git revert <sha>` and push.
To redeploy without changes, use **Actions → Build and deploy CV → Run workflow**.
