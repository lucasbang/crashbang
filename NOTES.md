# Notes

What was built and why, in order, and what's still open. How to *use*
the site is in `README.md`.

## 2026-11-20: from placeholder to publishing system

### Starting point

The repo held only `CNAME` and a hand-written `index.html`: a large `⨳!`
(U+2A33 SMASH PRODUCT + `!`, "crash bang", a pun on `#!`) over
`crashbang.sh █` on near-black. GitHub Pages served the repo root.
The brief for this work was `instructions.md` (kept locally, untracked).

### Build system

- **Pandoc renders everything; Python only organises.** `scripts/build.py`
  (stdlib only) finds posts and pages, sorts, groups and writes the feed, and
  runs pandoc for every page. It never parses YAML: front matter comes from
  `pandoc --template templates/meta.json` (`$meta-json$`). It never writes
  HTML: generated pages (home, log, archive, tags) are pandoc runs on empty
  input with a JSON `--metadata-file`, and the templates loop over the data.
- **Makefile does orchestration:** wipe `docs/`, copy `static/`, run
  `build.py`, copy `CNAME`, touch `docs/.nojekyll`. Targets: `build`,
  `preview`, `deploy`, `new`, `check`, `clean`.
- **URLs:** posts at `/log/YYYY/MM/DD/slug/`; any other `content/**.md` becomes
  `/<path>/`, leaving room for projects/works sections later.
  `static/works/<name>/` is served untouched at `/works/<name>/`.
- **Feed:** Atom 1.0 at `/feed.xml` built with ElementTree (handles
  escaping), full post HTML as content, latest 20 posts.
- **Related posts:** up to 3 posts sharing the most tags
  (`related_posts()` in `build.py`).
- `pandoc --wrap=none` is set because otherwise pandoc wraps long titles in
  template output (`First\nPost`).

### Design

- Palette from the placeholder (`#111111`, `#f3f0e8`, `#77736b`), all in
  CSS custom properties in `static/css/crashbang.css`.
- Monospace for chrome (paths, nav, dates, tags, code); system sans for prose.
- Homepage keeps the big `⨳!` + blinking cursor as the dominant element,
  then `~/log` recent posts. Other pages: `⨳! ~/path/to/page` breadcrumb,
  `~/log ~/archive ~/tags ~/about` nav, `exit 0` footer.
- Iterations after first look:
  - favicon: the space between `⨳` and `!` was removed; they're now two
    separately placed glyphs (`static/favicon.svg`).
  - `EOF` marker at the end of posts: removed (didn't like it).
  - column width: 40rem → 60rem (too wide) → **48rem** (about 80
    characters per line of prose).
  - homepage: the mark used to be centred in 72vh, which left too much space;
    now fixed padding (4rem top, 2.5rem on phones), and the domain line sits
    closer to the mark (`.mark span` line-height 0.9, `.domain` margin 0.5rem).

### Deployment

- First `make deploy` (commit `ba65ceb`) worked, but crashbang.sh showed the
  README rendered by Jekyll: Pages was still serving `/` (root).
- Switched Pages to `main` `/docs` with `gh api`, then had to request a
  build explicitly (changing the source doesn't trigger one). Verified that
  all main URLs return 200 on the live domain.

### xbstrxct import (staged, local only)

- The old xbstrxct writing lives in `~/Sync/abstraction-site/`, in five
  generations. The newest is the Quartz site `xbstrxct.com/content/`
  (commit `db86b25`, 2026-10-17); `archive/NOT-IN-SITE.md` there confirms
  every older copy was diffed against it and none has anything it lacks.
- Copied verbatim to `staging/xbstrxct/`: 7 essays (`blurbs/`), 6 concept
  notes, the "Software in the Natural World" reading (draft), images,
  bibliography. `staging/` is **gitignored**, because the repo is public. Its
  own `README.md` lists the Quartz syntax to convert when moving a piece over.

### Citations and drafts

- `--citeproc` against `bibliography/bibliography.bib` +
  `chicago-author-date.csl` (copied from xbstrxct) for every page, with a
  "References" section, linked citations, and CSS for the list.
- `draft: true` posts are skipped unless `build.py --drafts` /
  `make preview DRAFTS=1`. `make deploy` rebuilds without drafts, unstages
  draft source files and refuses `DRAFTS=1`.

### First imported post: Simondon (draft)

- `content/log/2026-11-20-simondon.md`, from `staging/xbstrxct/blurbs/simondon.md`
  (originally dated 2025-02-01; redated to 2026-11-20 on request), `draft: true`.
- Changes from the original: front-matter `image`/`imageAlt`/`imageCaption`
  → body figure at 50% width (`static/images/simondon-cadillac-1912.jpg`);
  `[[concretization]]` → plain *concretization*; the link to the Heidegger
  essay → plain text. The citation `[-@simondon2017mode]` renders natively.

### First Post date

The brief's test post was dated 2026-11-21 (tomorrow at the time). It was
changed to 2026-11-20 and the file renamed; its URL moved to
`/log/2026/11/20/first-post/`.

## 2026-11-23: easier draft previews

- **`make drafts`**: new shorthand target for `make preview DRAFTS=1`
  (`$(MAKE) preview DRAFTS=1`, so `PORT=` still passes through). The draft
  previewed at `/log/2026/11/20/simondon/`.
- **No more "Address already in use".** Running `make drafts` while a preview
  server was still up rebuilt `docs/` fine but then crashed starting a second
  server on port 8000. `preview` now tries to connect to `127.0.0.1:$(PORT)`
  first; if something answers, it prints "server already running … refresh the
  browser" and exits cleanly, otherwise it starts the server as before. The
  running server keeps serving the rebuilt `docs/` (it's given the path, and
  `docs/` is re-created in place), checked with a 200 on the Simondon URL.
- Caveat: the check only knows that *something* is on the port, not that it's
  our preview. If another program holds 8000, use `PORT=8001`.
- README "Drafts" section updated for both.

## Open items

- **Not yet deployed:** the citations/drafts machinery, the First Post date
  fix, and the CSS tweaks since the first deploy. The next `make deploy`
  publishes them. The live site still has First Post at `/log/2026/11/21/…`.
- **Simondon is a draft.** To publish: delete `draft: true`, then `make deploy`.
  Before that, decide whether to restore the Heidegger link (once that essay is
  imported) and the concretization link (if concept/glossary pages are added).
- **Goes public on the next deploy, though nothing links to it yet:** the Cadillac image
  (anything in `static/` gets copied into the site) and `bibliography/`.
- **Remaining staged essays:** Heidegger, ancient Greek formal methods,
  symbolic reasoning, Llull–Leibniz, Locke/SICP, Rotman, plus concept notes
  and the "Software in the Natural World" reading (uses callouts and `$math$`,
  which would need `--mathjax`/`--katex`).
- **Same-day ordering** falls back to reverse alphabetical title order. If
  that matters, add a time to dates or an explicit tiebreak field.
- `instructions.md` is untracked and not staged by deploy; delete or keep as
  you like.

## 2026-11-27: PDF export

- `make pdf POST=<slug|path>` → `staging/<slug>.pdf`, via pandoc + xelatex
  and `scripts/pdf.lua`. Made for sending the Simondon draft around. Output
  stays in gitignored `staging/`; the filter itself is tracked (in `scripts/`).
- Web-only bits: embeds become a "Video: <link>" line (YouTube embed URLs are
  rewritten to `watch?v=` links), other raw HTML is dropped, margin notes
  become footnotes, `/images/` maps to `static/images/`. Font TeX Gyre Pagella,
  1in margins.
- If a post gains something else HTML-only (callouts, `$math$`), the filter
  may need a rule for it.
