#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from collections import defaultdict

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

R2_GALLERIES_REL = Path("assets/private-plots/r2_galleries.json")


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(30):
        if (cur / ".git").exists() or (cur / "_config.yml").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError(f"Could not find repo root walking up from {start} (no .git or _config.yml found).")


def natural_sort_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def list_images(dir_path: Path) -> list[Path]:
    imgs = [p for p in dir_path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(imgs, key=lambda p: natural_sort_key(p.name))


def write_gallery_index(dir_path: Path, title: str, back_href: str | None) -> int:
    images = list_images(dir_path)
    names = [p.name for p in images]

    # Build thumbnail cards
    thumbs_html = []
    for i, name in enumerate(names):
        thumbs_html.append(f"""
    <div class="card">
      <button class="thumbBtn" data-idx="{i}" aria-label="Open {name}">
        <img class="thumb" src="{name}" loading="lazy" />
      </button>
      <div class="name">{name}</div>
    </div>
""".rstrip())

    # JS needs a JSON-ish array of strings (safe for filenames)
    # We’ll escape backslashes and quotes minimally.
    def js_str(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    images_js = ", ".join(js_str(n) for n in names)

    back_link_html = f'<div><a href="{back_href}">← Back</a></div>' if back_href else ""

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="noindex, nofollow"/>
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      margin: 24px;
      max-width: 1200px;
    }}
    .top {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }}
    .meta {{
      color: #666;
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 14px;
    }}
    .card {{
      border: 1px solid #eee;
      border-radius: 10px;
      padding: 10px;
    }}
    .thumbBtn {{
      all: unset;
      cursor: zoom-in;
      display: block;
    }}
    .thumb {{
      width: 100%;
      height: auto;
      border-radius: 8px;
      display: block;
    }}
    .name {{
      margin-top: 8px;
      font-size: 13px;
      color: #444;
      word-break: break-all;
    }}

    /* Lightbox */
    .lb {{
      position: fixed;
      inset: 0;
      display: none;
      background: rgba(0,0,0,0.92);
      z-index: 9999;
    }}
    .lb.open {{ display: block; }}
    .lbTop {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      z-index: 3;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      color: #fff;
      font-size: 14px;
      background: linear-gradient(to bottom, rgba(0,0,0,0.65), rgba(0,0,0,0));
    }}
    .lbBtn {{
      all: unset;
      cursor: pointer;
      padding: 6px 10px;
      border-radius: 10px;
      background: rgba(255,255,255,0.12);
    }}
    .lbBtn:hover {{ background: rgba(255,255,255,0.18); }}
    .lbStage {{
      position: absolute;
      inset: 0;
      z-index: 2;
      display: grid;
      place-items: center;
      padding: 52px 18px 18px 18px;
    }}
    .lbImg {{
      max-width: min(96vw, 1400px);
      max-height: 90vh;
      width: auto;
      height: auto;
      border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.4);
      cursor: default;
      user-select: none;
    }}
    .lbCaption {{
      position: absolute;
      bottom: 10px;
      left: 0;
      right: 0;
      text-align: center;
      color: rgba(255,255,255,0.85);
      font-size: 13px;
      padding: 8px 14px;
    }}
    .lbNav {{
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      width: 56px;
      height: 56px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      color: #fff;
      background: rgba(255,255,255,0.12);
      cursor: pointer;
      user-select: none;
    }}
    .lbNav:hover {{ background: rgba(255,255,255,0.18); }}
    .lbPrev {{ left: 16px; }}
    .lbNext {{ right: 16px; }}
    @media (max-width: 640px) {{
      .lbNav {{ width: 46px; height: 46px; }}
      .lbPrev {{ left: 10px; }}
      .lbNext {{ right: 10px; }}
    }}
  </style>
</head>
<body>
  <div class="top">
    <div>
      <h1 style="margin: 0 0 6px 0;">{title}</h1>
      <div class="meta">{len(names)} image(s)</div>
    </div>
    {back_link_html}
  </div>

  <div class="grid">
{chr(10).join(thumbs_html)}
  </div>

  <!-- Lightbox overlay -->
  <div class="lb" id="lb" role="dialog" aria-modal="true" aria-label="Image viewer">
    <div class="lbTop">
      <div id="lbInfo"></div>
      <div style="display:flex; gap:10px; align-items:center;">
        <a class="lbBtn" id="lbOpen" href="#" target="_blank" rel="noopener">Open</a>
        <button class="lbBtn" id="lbClose" aria-label="Close (Esc)">Close</button>
      </div>
    </div>

    <div class="lbStage" id="lbStage">
      <div class="lbNav lbPrev" id="lbPrev" aria-label="Previous (Left Arrow)">&#x2039;</div>
      <img class="lbImg" id="lbImg" alt="">
      <div class="lbNav lbNext" id="lbNext" aria-label="Next (Right Arrow)">&#x203A;</div>
      <div class="lbCaption" id="lbCaption"></div>
    </div>
  </div>

  <script>
    const IMAGES = [{images_js}];
    const lb = document.getElementById('lb');
    const lbImg = document.getElementById('lbImg');
    const lbCaption = document.getElementById('lbCaption');
    const lbInfo = document.getElementById('lbInfo');
    const lbOpen = document.getElementById('lbOpen');

    let idx = 0;

    function clampIndex(i) {{
      const n = IMAGES.length;
      return (i % n + n) % n;
    }}

    function setHash(i) {{
      // keep it simple; avoids interfering with Jekyll routing
      history.replaceState(null, "", `#img=${{i}}`);
    }}

    function readHash() {{
      const m = location.hash.match(/img=(\\d+)/);
      return m ? parseInt(m[1], 10) : null;
    }}

    function show(i, set_url=true) {{
      if (!IMAGES.length) return;
      idx = clampIndex(i);
      const name = IMAGES[idx];
      lbImg.src = name;
      lbImg.alt = name;
      lbCaption.textContent = name;
      lbInfo.textContent = `${{idx+1}} / ${{IMAGES.length}}`;
      lbOpen.href = name;
      lb.classList.add('open');
      if (set_url) setHash(idx);
      // prevent background scroll
      document.documentElement.style.overflow = "hidden";
      document.body.style.overflow = "hidden";
    }}

    function close() {{
      lb.classList.remove('open');
      // restore scroll
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
      // remove hash without jumping
      history.replaceState(null, "", location.pathname + location.search);
    }}

    function next() {{ show(idx + 1); }}
    function prev() {{ show(idx - 1); }}

    // Thumbnail clicks
    document.querySelectorAll('.thumbBtn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        const i = parseInt(btn.dataset.idx, 10);
        show(i);
      }});
    }});

    // Controls
    document.getElementById('lbClose').addEventListener('click', close);
    document.getElementById('lbNext').addEventListener('click', next);
    document.getElementById('lbPrev').addEventListener('click', prev);

    // Click outside image closes; click on left/right half of stage navigates
    document.getElementById('lbStage').addEventListener('click', (e) => {{
      if (e.target === lbImg) return; // clicking the image itself does nothing
      if (e.target.closest('.lbNav')) return; // nav buttons already handle clicks
      // If click is near edges, navigate; otherwise close
      const x = e.clientX;
      const w = window.innerWidth;
      if (x < w * 0.33) prev();
      else if (x > w * 0.67) next();
      else close();
    }});

    // Keyboard navigation
    window.addEventListener('keydown', (e) => {{
      if (!lb.classList.contains('open')) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight" || e.key === "l" || e.key === "j") next();
      else if (e.key === "ArrowLeft"  || e.key === "h" || e.key === "k") prev();
    }});

    // If someone loads the page with #img=N, open that image
    const initial = readHash();
    if (initial !== null && !Number.isNaN(initial)) {{
      show(initial, false);
      setHash(clampIndex(initial));
    }}
  </script>
</body>
</html>
"""
    (dir_path / "index.html").write_text(html, encoding="utf-8")
    return len(names)


def write_directory_hub_index(dir_path: Path, title: str, back_href: str | None, child_dirs: list[str]) -> None:
    child_links = "\n".join([f'    <li><a href="{name}/">{name}</a></li>' for name in child_dirs])
    back_link_html = f'<p><a href="{back_href}">← Back</a></p>' if back_href else ""
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="noindex, nofollow"/>
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      margin: 24px;
      max-width: 900px;
    }}
    .meta {{ color:#666; font-size:14px; margin-bottom: 12px; }}
    a {{ text-decoration: none; }}
    li {{ margin: 6px 0; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {back_link_html}
  <h2>Galleries</h2>
  <ul>
{child_links}
  </ul>
</body>
</html>
"""
    (dir_path / "index.html").write_text(html, encoding="utf-8")


def write_private_plots_404(private_plots_dir: Path) -> None:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="noindex, nofollow"/>
  <title>Private plots — Not found</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      margin: 24px;
      max-width: 900px;
    }
    .meta { color:#666; }
    a { text-decoration: none; }
  </style>
</head>
<body>
  <h1>Private plots: page not found</h1>
  <p class="meta">The requested path does not exist in the private-plots namespace.</p>
  <p><a href="/assets/private-plots/">Go to private-plots index</a></p>
</body>
</html>
"""
    (private_plots_dir / "404.html").write_text(html, encoding="utf-8")

def find_image_dirs(private_plots_dir: Path) -> list[Path]:
    """Return directories (including nested) that contain at least one image file."""
    dirs = set()
    for p in private_plots_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            dirs.add(p.parent)
    # deterministic order: shallow to deep, then name
    return sorted(dirs, key=lambda d: (len(d.relative_to(private_plots_dir).parts), str(d).lower()))


def url_for_dir(dir_path: Path, repo_root: Path) -> str:
    """
    Convert a filesystem directory to a site URL path.
    Assumes dir_path is under repo_root.
    """
    rel = dir_path.relative_to(repo_root).as_posix()
    return "/" + rel.strip("/") + "/"


def make_relative_back_href(current_dir: Path, target_dir: Path) -> str:
    """Relative link from current_dir/index.html to target_dir/index.html (or directory root)."""
    rel = target_dir.relative_to(current_dir).as_posix() if target_dir.is_relative_to(current_dir) else None
    if rel is not None:
        # target is inside current; just link directly
        return rel + "/"
    # otherwise compute a relative path via pathlib
    relpath = Path(os_relpath(target_dir, current_dir)).as_posix()
    return relpath.strip("/") + "/"


def os_relpath(target: Path, start: Path) -> str:
    # pathlib's relative_to only works for subpaths; this handles general case.
    import os
    return os.path.relpath(str(target), str(start))


def build_tree(private_plots_dir: Path, image_dirs: list[Path]) -> dict:
    """
    Build a nested dict tree of relative path parts for display.
    Only includes directories that have images (image_dirs).
    """
    tree: dict = {}
    for d in image_dirs:
        parts = d.relative_to(private_plots_dir).parts
        node = tree
        for part in parts:
            node = node.setdefault(part, {})
    return tree


def render_tree_html(tree: dict, base_url: str, prefix_parts: list[str] | None = None) -> str:
    """
    Render nested <ul> list. Each node is a directory. base_url is URL to assets/private-plots/.
    """
    prefix_parts = prefix_parts or []
    html = ["<ul>"]
    for name in sorted(tree.keys(), key=lambda s: natural_sort_key(s)):
        parts = prefix_parts + [name]
        url = base_url.rstrip("/") + "/" + "/".join(parts) + "/"
        html.append(f'  <li><a href="{url}">{"/".join(parts)}</a>')
        if tree[name]:
            html.append(render_tree_html(tree[name], base_url, parts))
        html.append("  </li>")
    html.append("</ul>")
    return "\n".join(html)


def load_r2_galleries(repo_root: Path) -> list[dict]:
    """Read the manifest of externally-hosted (R2) galleries, if present.

    These have no local filesystem trace -- the images live in R2, and the
    local copies used to upload them are deleted afterward -- so they can't
    be auto-discovered like local image_dirs. This manifest is the only
    record of them, and must be kept up to date by hand (or by whatever
    uploads to R2) whenever a gallery is added or removed.
    """
    manifest = repo_root / R2_GALLERIES_REL
    if not manifest.exists():
        return []
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    return sorted(entries, key=lambda e: natural_sort_key(e["name"]))


def render_external_galleries_html(entries: list[dict]) -> str:
    if not entries:
        return ""
    items = "\n".join(f'    <li><a href="{e["url"]}">{e["name"]}</a></li>' for e in entries)
    return f"""
  <h2>External galleries (Cloudflare R2)</h2>
  <p class="meta">Hosted outside this repo; listed in {R2_GALLERIES_REL.as_posix()}.</p>
  <ul>
{items}
  </ul>
"""


def main():
    script_path = Path(__file__).resolve()
    private_plots_dir = script_path.parent  # assets/private-plots/
    repo_root = find_repo_root(private_plots_dir)

    image_dirs = find_image_dirs(private_plots_dir)
    r2_entries = load_r2_galleries(repo_root)
    if not image_dirs and not r2_entries:
        print(f"[warn] No images found under {private_plots_dir} and no R2 galleries in {R2_GALLERIES_REL}. Nothing to do.")
        return

    # Create directory hubs for intermediate directories that don't contain images
    # but should still have an index (e.g., axion_plots/).
    hub_dirs = set()
    for d in image_dirs:
        cur = d.parent
        while cur != private_plots_dir and cur.is_relative_to(private_plots_dir):
            hub_dirs.add(cur)
            cur = cur.parent
    hub_dirs = sorted(hub_dirs - set(image_dirs), key=lambda p: natural_sort_key(p.name))

    relevant_dirs = set(image_dirs) | set(hub_dirs)

    # Write a top-level index.html overview in assets/private-plots/
    # (This will show images only if there are images directly in private-plots/;
    # but it's still useful as a landing page that links out.)
    # We'll make it a link hub, not a gallery, because images are in subdirs.
    base_url = url_for_dir(private_plots_dir, repo_root)

    # Create/overwrite index.html in every dir that contains images, unless it
    # opts out via a ".manual_index" marker file -- used for hand-written
    # article/report pages that live alongside their own images (e.g. a
    # literature-review writeup) rather than a generic auto-generated
    # thumbnail grid. Without this, re-running this script clobbers any
    # hand-crafted index.html the moment images are dropped in next to it.
    for d in image_dirs:
        if (d / ".manual_index").exists():
            print(f"[skip] {d / 'index.html'} is hand-written (.manual_index present), not regenerating")
            continue
        # Back link: if nested, go up one level; if top-level, go to /plots/
        if d == private_plots_dir:
            back_href = None
            title = "Private plots"
        else:
            back_href = None
            title = " / ".join(d.relative_to(private_plots_dir).parts)

        n = write_gallery_index(d, title=title, back_href=back_href)
        print(f"[ok] Wrote {d / 'index.html'} with {n} image(s)")

    # Create/overwrite index.html for directory hubs with links to child galleries/hubs
    for d in hub_dirs:
        if (d / ".manual_index").exists():
            print(f"[skip] {d / 'index.html'} is hand-written (.manual_index present), not regenerating")
            continue
        child_dirs = sorted([child.name for child in relevant_dirs if child.parent == d], key=natural_sort_key)
        title = " / ".join(d.relative_to(private_plots_dir).parts)
        back_href = None
        write_directory_hub_index(d, title=title, back_href=back_href, child_dirs=child_dirs)
        print(f"[ok] Wrote {d / 'index.html'} (hub with {len(child_dirs)} link(s))")

    # Write a top-level link hub index.html that lists all galleries --
    # local (in-repo) and external (R2). This file lives under
    # assets/private-plots/, so pushing it goes through the fast
    # deploy-private-plots.yml rsync path (~1 min end to end) instead of
    # the full Jekyll site build (~5 min) that _pages/plots.md would
    # trigger -- see R2_HOSTING.md. _pages/plots.md is a static page that
    # just links here and does not need to be regenerated when galleries
    # change.
    tree = build_tree(private_plots_dir, image_dirs)
    nested_list = render_tree_html(tree, base_url)
    external_html = render_external_galleries_html(r2_entries)

    hub = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="noindex, nofollow"/>
  <title>Private plots</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      margin: 24px;
      max-width: 900px;
    }}
    .meta {{ color:#666; font-size:14px; margin-bottom: 12px; }}
    a {{ text-decoration: none; }}
    li {{ margin: 6px 0; }}
  </style>
</head>
<body>
  <h1>Private plots</h1>
  <h2>Galleries</h2>
  {nested_list}
  {external_html}
</body>
</html>
"""
    (private_plots_dir / "index.html").write_text(hub, encoding="utf-8")
    print(f"[ok] Wrote {private_plots_dir / 'index.html'} (hub)")

    write_private_plots_404(private_plots_dir)
    print(f"[ok] Wrote {private_plots_dir / '404.html'}")

    if r2_entries:
        print(f"[ok] Included {len(r2_entries)} external (R2) gallery link(s) from {R2_GALLERIES_REL}")

    print("\nNext (fast path -- no full site rebuild needed):")
    print("  npx prettier assets/private-plots/index.html --write  # avoids a Prettier CI failure")
    print("  git add assets/private-plots/")
    print('  git commit -m "Update private plots galleries" && git push')
    print("  (deploy-private-plots.yml picks this up automatically, ~1 min)")


if __name__ == "__main__":
    main()