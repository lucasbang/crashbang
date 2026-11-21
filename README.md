# ⨳! crashbang.sh

A tiny static site. Markdown in `content/`, rendered by Pandoc into `docs/`,
committed, and served as plain files by GitHub Pages.

```
make build      # content/ -> docs/
make preview    # build, then serve on http://localhost:8000
make deploy MSG="new post: first post"
```

## Required tools

- `pandoc` (2.11 or newer; built with 3.1)
- `python3` (3.9+, standard library only)
- `make`, `git`

```bash
sudo apt install pandoc python3 make git
```

`make build` stops with a clear message if `pandoc` or `python3` is missing.

## How it works

```
Makefile            orchestration: wipe docs/, copy static/, run build.py,
                    copy CNAME, create docs/.nojekyll
scripts/build.py    finds posts and pages, sorts by date, builds the log,
                    archive, tag pages, related posts and feed.xml;
                    runs pandoc for every page
templates/          Pandoc HTML templates (all HTML lives here)
content/            Markdown you write
static/             files copied into docs/ as-is
docs/               generated site (committed; do not edit by hand)
staging/            local drafts and imports; never built, gitignored
```

`build.py` never parses YAML or writes HTML itself:

- front matter is read by asking Pandoc for it
  (`pandoc -t plain --template templates/meta.json`, where that template is
  just `$meta-json$`);
- generated pages (home, `/log/`, `/archive/`, `/tags/…`) are made by giving
  Pandoc a JSON metadata file with the post lists, and the templates loop over
  it with `$for(posts)$ … $endfor$`.

Templates:

| file | used for |
|---|---|
| `home.html` | `/` — the big ⨳! mark plus recent posts |
| `post.html` | every post in `content/log/` |
| `default.html` | every other page, plus the log, archive and tag listings |
| `_head.html`, `_nav.html`, `_path.html`, `_postlist.html`, `_foot.html` | shared partials, included with `${ _name() }` |
| `meta.json` | front-matter extraction (see above) |

Settings (site URL, number of posts on the homepage / in the feed / in
"see also") are constants at the top of `scripts/build.py`.

## Writing a post

```bash
make new TITLE="Some Title"         # creates content/log/YYYY-MM-DD-some-title.md
micro content/log/2026-11-21-some-title.md
make preview
make deploy MSG="new post: some title"
```

Or just create the file by hand:

```markdown
---
title: First Post
date: 2026-11-21
slug: first-post        # optional; defaults to the filename minus the date
tags:
  - meta
  - crashbang
description: optional one-line summary (meta description, feed summary)
draft: true             # optional; drafts are skipped by the build
---

Text in ordinary Pandoc Markdown.
```

`title` and `date` (YYYY-MM-DD) are required. The post appears at
`/log/YYYY/MM/DD/slug/`. Titles are Markdown, so `*emphasis*` works; avoid
raw HTML in titles.

## Pages and URLs

Any Markdown file in `content/` outside `content/log/` becomes a page:

```
content/index.md             -> /            (text appears under the mark)
content/about.md             -> /about/
content/projects/index.md    -> /projects/
content/projects/thing.md    -> /projects/thing/
```

A page may set `template: name` in its front matter to use
`templates/name.html` instead of `default.html`.

Generated:

```
/log/          all posts, newest first
/archive/      grouped by year and month
/tags/         tag index
/tags/<tag>/   posts with that tag
/feed.xml      Atom feed (latest 20 posts, full content)
```

## Static files

Everything in `static/` is copied to the site root unchanged:

```
static/css/crashbang.css   -> /css/crashbang.css
static/images/x.png        -> /images/x.png
static/pdf/x.pdf           -> /pdf/x.pdf
static/media/x.mp4         -> /media/x.mp4
static/js/x.js             -> /js/x.js
static/works/example/      -> /works/example/   (standalone HTML/JS pieces)
static/favicon.svg         -> /favicon.svg
```

## Rich content in posts

Pandoc passes raw HTML through, so all of these work inside Markdown:

```markdown
![a caption](/images/photo.jpg)

[the paper (PDF)](/pdf/paper.pdf)

<iframe class="pdf" src="/pdf/paper.pdf"></iframe>

<div class="embed">
  <iframe src="https://www.youtube-nocookie.com/embed/VIDEO_ID" allowfullscreen></iframe>
</div>

<div class="embed">
  <iframe src="https://player.vimeo.com/video/VIDEO_ID" allowfullscreen></iframe>
</div>

<video controls>
  <source src="/media/example.mp4" type="video/mp4">
</video>

<div id="simulation"></div>
<script src="/js/simulation.js"></script>
```

`.embed` makes a responsive 16:9 box; `.pdf` makes a tall PDF frame. Both
are defined in `static/css/crashbang.css`.

A fully standalone piece (its own `index.html`, scripts, assets) goes in
`static/works/<name>/` and is served untouched at `/works/<name>/`.

## Related posts

Each post lists up to 3 others that share the most tags (newest first on a
tie). The logic is `related_posts()` in `scripts/build.py`; the markup is the
`$if(related)$` block in `templates/post.html`. Delete that block to hide them.

## Deploying

`make deploy` builds, stages these paths only:

```
content templates static scripts docs Makefile README.md CNAME .gitignore
```

then commits with `MSG` (default: `update site`) and pushes. If nothing
changed it says so and does nothing. Other files in the repo are never
staged by it.

## GitHub Pages setup (one time)

In the repository on GitHub: **Settings → Pages**

- Source: **Deploy from a branch**
- Branch: **main**, folder: **/docs**
- Custom domain: **crashbang.sh** (the build also copies `CNAME` into `docs/`)
- Enforce HTTPS: on

`docs/.nojekyll` turns off Jekyll, so files are served exactly as built.

The old site served `index.html` from the repo root. After the first deploy
of this layout the site will 404 until the Pages folder is switched to
`/docs`.
