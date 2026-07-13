# Publishing plot galleries via Cloudflare R2

Runbook for adding a new hidden/unlinked plot gallery to msilvafe-cmb.com,
hosted on R2 instead of committed to this repo. Written so another agent
(or future you) can follow it without re-deriving the setup from scratch.

## Why this exists

Plots go on `/plots/` — a page with `nav: false`, `sitemap: false`, and a
`noindex, nofollow` meta tag, so it's reachable by direct URL but never
linked from the site or indexed. Images live in the `msilvafe-plots` R2
bucket instead of this git repo, so the repo's history doesn't grow with
binary plot files (git never shrinks; every version of every image would
stay in history forever).

There's also an older, still-valid path for *small* galleries: dropping
images into `assets/private-plots/<name>/` and running
`build_private_plots.py`, which auto-generates the gallery HTML and
commits straight into this repo. Use R2 (this doc) once a gallery is more
than a handful of images, or whenever avoiding repo growth matters more
than convenience.

## Page structure (why it's fast)

`_pages/plots.md` is a **static** page that just links to
`/assets/private-plots/` and never needs to change when galleries come and
go. All the actual gallery links — local and R2 alike — live in
`assets/private-plots/index.html`, which `build_private_plots.py`
regenerates from two sources every run:

- local galleries: auto-discovered by scanning `assets/private-plots/`
  for image directories
- external (R2) galleries: read from `assets/private-plots/r2_galleries.json`,
  a manifest of `{"name": ..., "url": ...}` entries — needed because R2
  galleries have no local filesystem trace once the upload copies are
  deleted (see step 6 below)

This matters because `assets/private-plots/**` changes deploy via
`deploy-private-plots.yml`, a plain `rsync` straight to the `gh-pages`
branch — no Ruby, no Jekyll, no CSS purge, **~1 minute total** (15s rsync
+ ~25s GitHub Pages redeploy). `_pages/plots.md` changes instead trigger
the full Jekyll site build (`deploy.yml`), which takes ~5 minutes and is
excluded from normal push triggers for exactly that reason. Editing
`plots.md` should be rare; editing `r2_galleries.json` should be the norm.

## Prerequisites

- Repo cloned locally with a clean `git status`.
- `boto3` installed (`pip install boto3`).
- R2 credentials available as environment variables for the one upload
  command (do not hardcode them in any file, do not commit them, and
  avoid pasting them into a chat transcript — write them to a local,
  non-repo file instead and read from there). Required variables:
  - `R2_ACCOUNT_ID`
  - `R2_ACCESS_KEY_ID`
  - `R2_SECRET_ACCESS_KEY`
  - `R2_BUCKET_NAME` (currently `msilvafe-plots`)
  - Public bucket URL: `https://pub-9a2228fc2c10456ba1753e60a6b9a06d.r2.dev`

If credentials aren't available yet, they come from the Cloudflare
dashboard: R2 → Manage API Tokens → Create API Token, scoped to **Object
Read & Write on this bucket only** (not full account access).

## Steps

1. **Stage the images locally**, one directory per gallery, e.g.:

   ```
   assets/private-plots/<topic>/<gallery-name>/
     01_first_plot.png
     02_second_plot.png
     ...
   ```

   Numeric prefixes control display order (natural sort). Use descriptive
   filenames — they're shown as captions in the gallery viewer.

2. **Generate a gallery `index.html`** by running the normal generator —
   this also regenerates the top-level hub, which is fine:

   ```bash
   python3 assets/private-plots/build_private_plots.py
   ```

3. **Upload to R2** (images plus the generated `index.html`):

   ```bash
   cd assets/private-plots
   R2_ACCOUNT_ID=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... R2_BUCKET_NAME=msilvafe-plots \
     python3 upload_to_r2.py <topic>/<gallery-name> <topic>/<gallery-name>
   ```

   (First arg = local directory, second = R2 key prefix. Keeping them
   identical mirrors the local layout in the bucket, which keeps things
   predictable.)

4. **Verify the upload is publicly reachable** before wiring up links —
   catches typos/permission issues immediately instead of via a failed CI
   check later:

   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" \
     "https://pub-9a2228fc2c10456ba1753e60a6b9a06d.r2.dev/<topic>/<gallery-name>/index.html"
   ```

   Should print `200`.

5. **Add an entry to `assets/private-plots/r2_galleries.json`** (a plain
   JSON array — add yours, keep the rest):

   ```json
   {"name": "<topic>/<gallery-name>", "url": "https://pub-9a2228fc2c10456ba1753e60a6b9a06d.r2.dev/<topic>/<gallery-name>/index.html"}
   ```

   **Link to `index.html` explicitly** — this is the one gotcha that
   isn't obvious: R2's public bucket URL does **not** auto-resolve
   directory-style URLs to their `index.html` the way GitHub Pages /
   most web servers do. A bare `.../gallery-name/` link 404s. This bit us
   on the first rollout — the repo's own "Check for broken links" CI
   caught it.

6. **Re-run the generator** so the hub page picks up the manifest change,
   then **remove the local gallery copy** — it only needed to exist long
   enough to upload:

   ```bash
   python3 assets/private-plots/build_private_plots.py
   rm -rf assets/private-plots/<topic>/<gallery-name>
   git status --short   # confirm nothing else unexpected is staged
   ```

   Re-running the generator also touches every other gallery's
   `index.html` as a side effect. Check `git diff --stat` on those and
   `git checkout --` any that are pure reformatting noise (compare image
   filenames before/after if unsure — see the script's own git history
   for the exact one-liner used to verify this), to keep the commit
   focused on the actual change.

7. **Commit and push** — should be just `assets/private-plots/index.html`
   (the hub) and `r2_galleries.json`. Nothing binary, nothing under
   `_pages/`.

   ```bash
   git add assets/private-plots/
   git commit -m "Add <topic>/<gallery-name> plot gallery"
   git push
   ```

8. **Verify — no manual deploy trigger needed.** `deploy-private-plots.yml`
   fires automatically on push to `assets/private-plots/**`. Wait about a
   minute, then:

   ```bash
   curl -s "https://msilvafe-cmb.com/assets/private-plots/" | grep -A 3 "<gallery-name>"
   ```

   If you ever *do* need to touch `_pages/plots.md` itself (rare — it's
   meant to stay static), that still requires a manual full-site deploy:
   `gh workflow run "Deploy site" --repo msilvafe/msilvafe.github.io --ref main`
   (~5 min, `gh run watch <run-id>` to wait for it).

## After finishing

If credentials were ever typed into a chat/terminal transcript rather than
read from a local file, rotate the R2 API token afterward (Cloudflare
dashboard → R2 → Manage API Tokens → revoke old, create new) — cheap
insurance, doesn't affect anything already uploaded.
