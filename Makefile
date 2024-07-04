all:

.PHONY: update_deps clean check format help

UPDATE_DEPS_ENV = .env-deps
LINT_ENV = .env-lint

SOURCES = hwbench setup.py csv graph

update_env:
	python3 -m venv $(UPDATE_DEPS_ENV)
	./$(UPDATE_DEPS_ENV)/bin/pip install --upgrade --quiet pip-tools

update_deps: update_env
	./$(UPDATE_DEPS_ENV)/bin/pip-compile --upgrade --output-file=requirements/base.txt requirements/base.in
	./$(UPDATE_DEPS_ENV)/bin/pip-compile --upgrade --output-file=requirements/test.txt requirements/test.in

regen_hashes: update_env
	./$(UPDATE_DEPS_ENV)/bin/pip-compile --output-file=requirements/base.txt requirements/base.in
	./$(UPDATE_DEPS_ENV)/bin/pip-compile --output-file=requirements/test.txt requirements/test.in

clean:
	rm -fr $(UPDATE_DEPS_ENV) $(LINT_ENV)

$(LINT_ENV):
	python3 -m venv $(LINT_ENV)
	./$(LINT_ENV)/bin/pip install -r requirements/test.txt

check: $(LINT_ENV)
	env PYTHON=python3 ./$(LINT_ENV)/bin/tox

bundle: $(LINT_ENV)
	env PYTHON=python3 ./$(LINT_ENV)/bin/tox -e bundle

format: $(LINT_ENV)
	./$(LINT_ENV)/bin/ruff format $(SOURCES)

help:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'
