#!/usr/bin/env python3
"""
crashbang.sh site builder.

Reads Markdown from content/, renders it with Pandoc and the templates in
templates/, and writes HTML into docs/. Python standard library only.

What this script does:
    - finds posts in content/log/ and pages everywhere else in content/
    - reads front matter by asking Pandoc for it (no YAML parsing here)
    - works out URLs, sorts posts by date, groups the archive, collects tags
    - picks related posts by shared tags
    - writes the Atom feed

What it does not do (see the Makefile): clean docs/, copy static/, CNAME,
.nojekyll.

All HTML comes from Pandoc templates. For generated pages (home, log,
archive, tags) this script writes a small JSON metadata file and runs Pandoc
on empty input, and the template loops over the data.
"""

import atexit
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# --- settings -------------------------------------------------------------

SITE_URL = "https://crashbang.sh"
SITE_TITLE = "crashbang.sh"

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
OUT = ROOT / "docs"
POSTS_DIR = CONTENT / "log"

HOME_POSTS = 5       # posts listed on the homepage
FEED_POSTS = 20      # posts in feed.xml
RELATED_POSTS = 3    # "see also" links under each post

PANDOC_COMMON = [
    "--from=markdown",
    "--to=html5",
    "--highlight-style=breezedark",
    "--wrap=none",
]

TMP = Path(tempfile.mkdtemp(prefix="crashbang-"))
atexit.register(shutil.rmtree, TMP, ignore_errors=True)


# --- helpers --------------------------------------------------------------

def die(msg):
    sys.exit(f"error: {msg}")


def pandoc(args, input_text=None):
    """Run pandoc, return stdout. Stop the build on failure."""
    try:
        result = subprocess.run(
            ["pandoc", *args],
            input=input_text,
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        die("pandoc not found. Install it (e.g. `sudo apt install pandoc`).")
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode != 0:
        die(f"pandoc failed: pandoc {' '.join(map(str, args))}")
    return result.stdout


def read_meta(path):
    """Front matter of a Markdown file, as plain strings/lists, via Pandoc."""
    out = pandoc(["--to=plain", f"--template={TEMPLATES / 'meta.json'}", str(path)])
    return json.loads(out)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def write_meta_file(data):
    """Write data as a Pandoc --metadata-file (JSON is valid YAML)."""
    f = tempfile.NamedTemporaryFile("w", suffix=".json", dir=TMP, delete=False)
    json.dump(data, f)
    f.close()
    return f.name


def render(template, out_path, data, source=None):
    """Render `source` (a Markdown file, or nothing) through a template."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        *PANDOC_COMMON,
        "--standalone",
        f"--template={TEMPLATES / template}",
        f"--metadata-file={write_meta_file(data)}",
        f"--output={out_path}",
    ]
    if source:
        pandoc([*args, str(source)])
    else:
        pandoc(args, input_text="")
    print(f"  {out_path.relative_to(ROOT)}")


def pagetitle(title):
    return f"{title} · {SITE_TITLE}" if title else SITE_TITLE


def crumbs(url):
    """'/log/2026/11/21/x/' -> path segments for the ~/... breadcrumb.

    Only segments that are real pages get links.
    """
    parts = [p for p in url.strip("/").split("/") if p]
    out = []
    for i, name in enumerate(parts):
        href = "/" + "/".join(parts[: i + 1]) + "/"
        out.append({"name": name, "url": href if href in KNOWN_URLS else ""})
    return out


# URLs that will exist once the build finishes (filled in main()).
KNOWN_URLS = set()


# --- posts ----------------------------------------------------------------

def load_posts():
    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        meta = read_meta(path)
        if str(meta.get("draft", "")).lower() == "true":
            print(f"  (draft, skipped) {path.relative_to(ROOT)}")
            continue

        title = meta.get("title")
        if not title:
            die(f"{path.relative_to(ROOT)}: missing `title:` in front matter")
        try:
            date = dt.date.fromisoformat(str(meta.get("date", "")))
        except ValueError:
            die(f"{path.relative_to(ROOT)}: `date:` must look like 2026-11-21")

        default_slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
        slug = slugify(meta.get("slug") or default_slug)
        tags = [str(t) for t in as_list(meta.get("tags"))]
        url = f"/log/{date:%Y/%m/%d}/{slug}/"

        posts.append({
            "path": path,
            "title": title,
            "date": date,
            "slug": slug,
            "tags": tags,
            "url": url,
            "description": meta.get("description", ""),
        })

    urls = [p["url"] for p in posts]
    dupes = {u for u in urls if urls.count(u) > 1}
    if dupes:
        die(f"two posts share a URL: {', '.join(sorted(dupes))}")

    posts.sort(key=lambda p: (p["date"], p["title"]), reverse=True)
    return posts


def summary(post):
    """The bits of a post that listing templates need."""
    return {"title": post["title"], "date": post["date"].isoformat(), "url": post["url"]}


def related_posts(post, posts):
    """Posts sharing the most tags with `post`; ties go to the newer post.

    To change how related posts are chosen, change this function.
    """
    mine = set(post["tags"])
    scored = []
    for other in posts:
        if other is post:
            continue
        shared = len(mine & set(other["tags"]))
        if shared:
            scored.append((shared, other["date"], other))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [summary(o) for _, _, o in scored[:RELATED_POSTS]]


def build_posts(posts):
    for post in posts:
        data = {
            "pagetitle": pagetitle(post["title"]),
            "crumbs": crumbs(post["url"]),
            "tag_links": [{"name": t, "url": f"/tags/{slugify(t)}/"} for t in post["tags"]],
            "related": related_posts(post, posts),
        }
        out = OUT / post["url"].strip("/") / "index.html"
        render("post.html", out, data, source=post["path"])


# --- pages ----------------------------------------------------------------

def page_url(path):
    """content/about.md -> /about/ ; content/x/index.md -> /x/"""
    rel = path.relative_to(CONTENT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "index":
        parts = parts[:-1]
    return "/" + "".join(p + "/" for p in parts)


def page_files():
    for path in sorted(CONTENT.rglob("*.md")):
        if POSTS_DIR in path.parents:
            continue
        yield path


def build_pages(posts):
    for path in page_files():
        meta = read_meta(path)
        url = page_url(path)
        out = OUT / url.strip("/") / "index.html"
        title = meta.get("title") or (path.stem if path.stem != "index" else "")

        if url == "/":
            data = {
                "pagetitle": SITE_TITLE,
                "posts": [summary(p) for p in posts[:HOME_POSTS]],
            }
            template = "home.html"
        else:
            data = {"pagetitle": pagetitle(title), "crumbs": crumbs(url)}
            # A page can pick another template with `template: name` in its
            # front matter (uses templates/name.html).
            template = f"{meta.get('template', 'default')}.html"

        render(template, out, data, source=path)


# --- generated listings ---------------------------------------------------

def build_log(posts):
    render("default.html", OUT / "log" / "index.html", {
        "pagetitle": pagetitle("log"),
        "crumbs": crumbs("/log/"),
        "posts": [summary(p) for p in posts],
    })


def build_archive(posts):
    years = []
    for post in posts:  # already newest first
        d = post["date"]
        if not years or years[-1]["year"] != str(d.year):
            years.append({"year": str(d.year), "months": []})
        months = years[-1]["months"]
        month_name = d.strftime("%B")
        if not months or months[-1]["month"] != month_name:
            months.append({"month": month_name, "posts": []})
        months[-1]["posts"].append({**summary(post), "day": f"{d.day:02d}"})

    render("default.html", OUT / "archive" / "index.html", {
        "pagetitle": pagetitle("archive"),
        "crumbs": crumbs("/archive/"),
        "years": years,
    })


def build_tags(posts):
    tags = {}
    names = {}
    for post in posts:
        for tag in post["tags"]:
            slug = slugify(tag)
            tags.setdefault(slug, []).append(post)
            names.setdefault(slug, tag)

    taglist = [
        {"name": names[s], "url": f"/tags/{s}/", "count": str(len(tags[s]))}
        for s in sorted(tags)
    ]
    render("default.html", OUT / "tags" / "index.html", {
        "pagetitle": pagetitle("tags"),
        "crumbs": crumbs("/tags/"),
        "taglist": taglist,
    })

    for slug, tagged in tags.items():
        render("default.html", OUT / "tags" / slug / "index.html", {
            "pagetitle": pagetitle(f"#{names[slug]}"),
            "crumbs": crumbs(f"/tags/{slug}/"),
            "posts": [summary(p) for p in tagged],
        })


# --- feed -----------------------------------------------------------------

def build_feed(posts):
    """Atom 1.0 (RFC 4287). ElementTree handles all XML escaping."""
    ATOM = "http://www.w3.org/2005/Atom"
    XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"

    def stamp(d):
        return f"{d.isoformat()}T00:00:00Z"

    def sub(parent, tag, text=None, **attrs):
        el = ET.SubElement(parent, tag, attrs)
        if text is not None:
            el.text = text
        return el

    recent = posts[:FEED_POSTS]
    feed = ET.Element("feed", {"xmlns": ATOM, XML_BASE: SITE_URL + "/"})
    sub(feed, "title", SITE_TITLE)
    sub(feed, "id", SITE_URL + "/")
    sub(feed, "link", href=SITE_URL + "/")
    sub(feed, "link", rel="self", href=SITE_URL + "/feed.xml")
    sub(feed, "updated", stamp(recent[0]["date"]) if recent else stamp(dt.date.today()))
    author = sub(feed, "author")
    sub(author, "name", SITE_TITLE)

    for post in recent:
        url = SITE_URL + post["url"]
        body = pandoc([*PANDOC_COMMON, str(post["path"])])
        entry = sub(feed, "entry")
        sub(entry, "title", post["title"])
        sub(entry, "id", url)
        sub(entry, "link", href=url)
        sub(entry, "published", stamp(post["date"]))
        sub(entry, "updated", stamp(post["date"]))
        for tag in post["tags"]:
            sub(entry, "category", term=tag)
        if post["description"]:
            sub(entry, "summary", post["description"])
        sub(entry, "content", body, type="html")

    out = OUT / "feed.xml"
    ET.indent(feed)
    ET.ElementTree(feed).write(out, encoding="utf-8", xml_declaration=True)
    print(f"  {out.relative_to(ROOT)}")


# --- main -----------------------------------------------------------------

def main():
    if shutil.which("pandoc") is None:
        die("pandoc not found. Install it (e.g. `sudo apt install pandoc`).")
    OUT.mkdir(exist_ok=True)

    print("posts")
    posts = load_posts()

    KNOWN_URLS.update({"/log/", "/archive/", "/tags/"})
    KNOWN_URLS.update(page_url(p) for p in page_files())
    KNOWN_URLS.update(f"/tags/{slugify(t)}/" for p in posts for t in p["tags"])

    build_posts(posts)
    print("pages")
    build_pages(posts)
    print("listings")
    build_log(posts)
    build_archive(posts)
    build_tags(posts)
    print("feed")
    build_feed(posts)


if __name__ == "__main__":
    main()
