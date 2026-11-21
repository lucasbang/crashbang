# crashbang.sh
#
#   make build                       render content/ into docs/
#   make preview                     build, then serve docs/ on localhost
#   make deploy MSG="new post: x"    build, commit, push
#   make new TITLE="Some Title"      start a new post in content/log/

PYTHON ?= python3
PORT   ?= 8000
MSG    ?= update site

# Paths committed by `make deploy`. Anything else (scratch files, notes)
# is left alone.
TRACKED = content templates static scripts docs Makefile README.md CNAME .gitignore

.PHONY: build check preview deploy new clean

build: check
	rm -rf docs
	mkdir -p docs
	cp -r static/. docs/
	find docs -name .gitkeep -delete
	$(PYTHON) scripts/build.py
	cp CNAME docs/CNAME
	touch docs/.nojekyll
	@echo "built docs/"

check:
	@command -v pandoc >/dev/null 2>&1 || { echo "error: pandoc not found (sudo apt install pandoc)"; exit 1; }
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "error: $(PYTHON) not found (sudo apt install python3)"; exit 1; }

preview: build
	@echo
	@echo "  http://localhost:$(PORT)"
	@echo
	$(PYTHON) -m http.server $(PORT) --bind 127.0.0.1 --directory docs

deploy: build
	git add -A $(TRACKED)
	@if git diff --cached --quiet; then \
		echo "nothing to deploy"; \
	else \
		git commit -m "$(MSG)" && git push; \
	fi

new:
	@test -n "$(TITLE)" || { echo 'usage: make new TITLE="Some Title"'; exit 1; }
	@slug=$$(echo "$(TITLE)" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$$//g'); \
	day=$$(date +%F); \
	file="content/log/$$day-$$slug.md"; \
	test ! -e "$$file" || { echo "error: $$file already exists"; exit 1; }; \
	printf -- '---\ntitle: %s\ndate: %s\nslug: %s\ntags: []\n---\n\n' "$(TITLE)" "$$day" "$$slug" > "$$file"; \
	echo "$$file"

clean:
	rm -rf docs
