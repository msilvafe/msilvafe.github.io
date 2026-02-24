#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

PLOTS_MD_REL = Path("_pages/plots.md")
START_MARKER = "<!-- PLOTS:START -->"
END_MARKER = "<!-- PLOTS:END -->"


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


def write_gallery_index(dir_path: Path, title: str, back_href: str) -> int:
    images = list_images(dir_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

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
  </style>
</head>
<body>
  <div class="top">
    <div>
      <h1 style="margin: 0 0 6px 0;">{title}</h1>
      <div class="meta">{len(images)} image(s) • Updated {now}</div>
    </div>
    <div><a href="{back_href}">← Back</a></div>
  </div>

  <div class="grid">
"""
    for img in images:
        name = img.name
        html += f"""    <div class="card">
      <a href="{name}">
        <img class="thumb" src="{name}" loading="lazy" />
      </a>
      <div class="name">{name}</div>
    </div>
"""

    html += """  </div>
</body>
</html>
"""
    (dir_path / "index.html").write_text(html, encoding="utf-8")
    return len(images)


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


def update_plots_md(repo_root: Path, private_plots_dir: Path, image_dirs: list[Path]):
    plots_md = repo_root / PLOTS_MD_REL
    if not plots_md.exists():
        raise FileNotFoundError(
            f"Can't find {plots_md}.\n"
            f"Create it at {PLOTS_MD_REL} relative to repo root: {repo_root}\n"
            f"and include the markers:\n  {START_MARKER}\n  {END_MARKER}"
        )

    text = plots_md.read_text(encoding="utf-8")
    if START_MARKER not in text or END_MARKER not in text:
        raise ValueError(f"{plots_md} must contain both markers:\n  {START_MARKER}\n  {END_MARKER}")

    base_url = url_for_dir(private_plots_dir, repo_root)  # e.g. /assets/private-plots/
    tree = build_tree(private_plots_dir, image_dirs)
    nested_list = render_tree_html(tree, base_url)

    lines = [
        START_MARKER,
        "",
        '<meta name="robots" content="noindex, nofollow">',
        "",
        "## Galleries",
        "",
        f'<p><a href="{base_url}">Top-level gallery index</a></p>',
        "",
        nested_list,
        "",
        END_MARKER,
    ]
    new_block = "\n".join(lines)

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), flags=re.DOTALL)
    new_text = pattern.sub(new_block, text, count=1)
    plots_md.write_text(new_text, encoding="utf-8")


def main():
    script_path = Path(__file__).resolve()
    private_plots_dir = script_path.parent  # assets/private-plots/
    repo_root = find_repo_root(private_plots_dir)

    image_dirs = find_image_dirs(private_plots_dir)
    if not image_dirs:
        print(f"[warn] No images found under {private_plots_dir}. Nothing to do.")
        return

    # Write a top-level index.html overview in assets/private-plots/
    # (This will show images only if there are images directly in private-plots/;
    # but it's still useful as a landing page that links out.)
    # We'll make it a link hub, not a gallery, because images are in subdirs.
    base_url = url_for_dir(private_plots_dir, repo_root)

    # Create/overwrite index.html in every dir that contains images
    for d in image_dirs:
        # Back link: if nested, go up one level; if top-level, go to /plots/
        if d == private_plots_dir:
            back_href = "/plots/"
            title = "Private plots"
        else:
            # link to parent directory index if parent is under private-plots; otherwise /plots/
            parent = d.parent
            back_href = "../" if parent.exists() else "/plots/"
            title = " / ".join(d.relative_to(private_plots_dir).parts)

        n = write_gallery_index(d, title=title, back_href=back_href)
        print(f"[ok] Wrote {d / 'index.html'} with {n} image(s)")

    # Write a top-level link hub index.html that lists all galleries
    tree = build_tree(private_plots_dir, image_dirs)
    nested_list = render_tree_html(tree, base_url)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
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
  <div class="meta">Updated {now}</div>
  <p><a href="/plots/">← Back to /plots/</a></p>
  <h2>Galleries</h2>
  {nested_list}
</body>
</html>
"""
    (private_plots_dir / "index.html").write_text(hub, encoding="utf-8")
    print(f"[ok] Wrote {private_plots_dir / 'index.html'} (hub)")

    # Update _pages/plots.md
    update_plots_md(repo_root, private_plots_dir, image_dirs)
    print(f"[ok] Updated {repo_root / PLOTS_MD_REL}")

    print("\nNext:")
    print("  git add assets/private-plots/**/index.html _pages/plots.md")
    print('  git commit -m "Auto-build private plots galleries" && git push')


if __name__ == "__main__":
    main()