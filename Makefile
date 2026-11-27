# crashbang.sh
#
#   make build                       render content/ into docs/
#   make preview                     build, then serve docs/ on localhost
#   make preview DRAFTS=1            same, including posts marked draft: true
#   make drafts                      shorthand for make preview DRAFTS=1
#   make deploy MSG="new post: x"    build, commit, push
#   make new TITLE="Some Title"      start a new post in content/log/
#   make kill-server                 stop a preview server left running on PORT
#   make pdf POST=simondon           render content/log/*-simondon.md to staging/simondon.pdf

PYTHON ?= python3
PORT   ?= 8000
MSG    ?= update site

# Paths committed by `make deploy`. Anything else (scratch files, notes)
# is left alone.
TRACKED = content templates static scripts bibliography docs Makefile README.md NOTES.md CNAME .gitignore

.PHONY: build check preview drafts deploy no-drafts new clean kill-server pdf

build: check
	rm -rf docs
	mkdir -p docs
	cp -r static/. docs/
	find docs -name .gitkeep -delete
	$(PYTHON) scripts/build.py $(if $(DRAFTS),--drafts)
	cp CNAME docs/CNAME
	touch docs/.nojekyll
	@echo "built docs/"

check:
	@command -v pandoc >/dev/null 2>&1 || { echo "error: pandoc not found (sudo apt install pandoc)"; exit 1; }
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "error: $(PYTHON) not found (sudo apt install python3)"; exit 1; }

# If an earlier preview is already serving PORT and answering, just rebuild
# and tell the user to refresh. If it's listening but not answering (a stale
# server), kill it and start a fresh one.
preview: build
	@echo
	@echo "  http://localhost:$(PORT)"
	@echo
	@if $(PYTHON) -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:$(PORT)/", timeout=2)' 2>/dev/null; then \
		echo "  server already running on port $(PORT): rebuilt docs/, refresh the browser"; \
	else \
		$(MAKE) --no-print-directory kill-server; \
		$(PYTHON) -m http.server $(PORT) --bind 127.0.0.1 --directory docs; \
	fi

# Kills the python process listening on PORT (an earlier preview), nothing else.
kill-server:
	@pids=$$(ss -ltnpH "sport = :$(PORT)" | grep -o 'python[^"]*",pid=[0-9]*' | grep -o '[0-9]*$$'); \
	if [ -n "$$pids" ]; then \
		kill $$pids && echo "stopped preview server on port $(PORT)"; sleep 0.5; \
	else \
		echo "no preview server running on port $(PORT)"; \
	fi

drafts:
	$(MAKE) preview DRAFTS=1

# Drafts are never deployed: the site is rebuilt without them, and draft
# source files are left out of the commit (the repo is public).
deploy: no-drafts build
	git add -A $(TRACKED)
	@drafts=$$(grep -l '^draft: *true' content/log/*.md 2>/dev/null); \
	if [ -n "$$drafts" ]; then \
		git reset -q -- $$drafts; \
		echo "not committing drafts:"; echo "$$drafts" | sed 's/^/  /'; \
	fi
	@if git diff --cached --quiet; then \
		echo "nothing to deploy"; \
	else \
		git commit -m "$(MSG)" && git push; \
	fi

no-drafts:
	@test -z "$(DRAFTS)" || { echo "error: don't deploy with DRAFTS set"; exit 1; }

new:
	@test -n "$(TITLE)" || { echo 'usage: make new TITLE="Some Title"'; exit 1; }
	@slug=$$(echo "$(TITLE)" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$$//g'); \
	day=$$(date +%F); \
	file="content/log/$$day-$$slug.md"; \
	test ! -e "$$file" || { echo "error: $$file already exists"; exit 1; }; \
	printf -- '---\ntitle: %s\ndate: %s\nslug: %s\ntags: []\n---\n\n' "$(TITLE)" "$$day" "$$slug" > "$$file"; \
	echo "$$file"

# PDF of one post, for reading or sending. Output goes to staging/, which is
# gitignored, so drafts stay local. Embeds become links, margin notes become
# footnotes (scripts/pdf.lua). Needs xelatex (texlive-xetex, tex-gyre).
pdf: check
	@test -n "$(POST)" || { echo 'usage: make pdf POST=<slug or path to .md>'; exit 1; }
	@command -v xelatex >/dev/null 2>&1 || { echo "error: xelatex not found (sudo apt install texlive-xetex tex-gyre)"; exit 1; }
	@src="$(POST)"; test -f "$$src" || src=$$(ls content/log/*-$(POST).md 2>/dev/null | head -n1); \
	test -n "$$src" && test -f "$$src" || { echo "error: no post matching $(POST)"; exit 1; }; \
	slug=$$(basename "$$src" .md | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}-//'); \
	mkdir -p staging; \
	pandoc "$$src" \
		--lua-filter=scripts/pdf.lua --citeproc \
		--bibliography=bibliography/bibliography.bib \
		--csl=bibliography/chicago-author-date.csl \
		-M reference-section-title=References -M link-citations=true \
		--pdf-engine=xelatex -V mainfont="TeX Gyre Pagella" \
		-V geometry:margin=1in -V colorlinks=true \
		-o "staging/$$slug.pdf" && echo "staging/$$slug.pdf"

clean:
	rm -rf docs
