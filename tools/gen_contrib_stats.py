import os, json
from datetime import date
from pathlib import Path
import urllib.parse
import urllib.request

USER = "msilvafe"
REPOS = [
    "simonsobs/sotodlib",
    "simonsobs/socs",
    "simonsobs/sodetlib",
]

def search_count(token: str, q: str) -> int:
    url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "contrib-stats-script",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode("utf-8"))
    return int(data.get("total_count", 0))

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not set. In PowerShell: $env:GITHUB_TOKEN='...'")

    stats = {}
    for repo in REPOS:
        stats[repo] = {
            "prs_opened": search_count(token, f"repo:{repo} is:pr author:{USER}"),
            "issues_opened": search_count(token, f"repo:{repo} is:issue author:{USER}"),
            "reviews": search_count(token, f"repo:{repo} is:pr reviewed-by:{USER}"),
        }

    out = [f'generated: "{date.today().isoformat()}"', "stats:"]
    for repo, s in stats.items():
        out += [
            f"  {repo}:",
            f"    prs_opened: {s['prs_opened']}",
            f"    issues_opened: {s['issues_opened']}",
            f"    reviews: {s['reviews']}",
        ]

    Path("_data").mkdir(exist_ok=True)
    Path("_data/contrib_stats.yml").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("Wrote _data/contrib_stats.yml")

if __name__ == "__main__":
    main()
