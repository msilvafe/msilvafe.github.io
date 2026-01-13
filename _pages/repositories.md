---
layout: page
title: Repositories
permalink: /repositories/
nav: true
description: A curated list of the public GitHub repositories that I actively contribute to. I also contribute to and maintain a number of private repositories for the HAYSTAC and ALPHA collaborations.
---

## GitHub Repositories

### [so_data_exploration](https://github.com/msilvafe/so_data_exploration)

**Description:** My personal scripts for parsing and visualizing SO (Simons Observatory) data products.

---

### [Simons-NSBP-Tutorial](https://github.com/msilvafe/Simons-NSBP-Tutorial)

**Description:** This is just a trial tutorial for folks to learn about basic GitHub and git operations which I built for a professional development series in the inaugural year of the Simons National Society of Black Physicists scholars summer program.

---

## Major contributions (selected)

{% assign user = site.data.contributed_repos.user %}

{% for item in site.data.contributed_repos.repos %}
{% assign repo = item.full_name %}
{% assign s = site.data.contrib_stats.stats[repo] %}

### [{{ repo }}](https://github.com/{{ repo }})

**Description:** {{ item.description }}

**My contribution statistics:**

- PRs opened: {{ s.prs_opened | default: "—" }}
- Issues opened: {{ s.issues_opened | default: "—" }}
- Reviews: {{ s.reviews | default: "—" }}

{% endfor %}
