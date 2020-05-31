.PHONY: install clean clean-build clean-pyc clean-test test lint isort coverage help
.DEFAULT_GOAL := help

PROJECT := mailman
VIRTUAL_ENV := venv

PYTHON_VERSION := python3
PYTHON_BIN := $(VIRTUAL_ENV)/bin

venv/bin/activate:
	test -d venv || $(PYTHON_VERSION) -m venv $(VIRTUAL_ENV)
	$(PYTHON_BIN)/python -m pip install --upgrade pip
	touch venv/bin/activate

venv: venv/bin/activate

install: venv
	$(PYTHON_BIN)/python -m pip install --editable .

clean: clean-build clean-pyc clean-test ## remove all build, test and Python artifacts

clean-build: ## remove build artifacts
	rm -rf .eggs/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name '*.egg' -delete

clean-pyc: ## remove Python artifacts
	find . -name '*.py[co]' -delete
	find . -name '*~'  -delete
	find . -name '__pycache__' -delete

clean-test: ## remove test and coverage artifacts
	rm -f .coverage
	rm -rf .tox/
	rm -rf htmlcov/

test: ## run test suite
	-tox

lint: ## check style with linter
	-tox -e lint

coverage: test ## run code coverage
	coverage report
	coverage html
	cd htmlcov && python -m http.server

isort: ## sort package imports with isort
	isort --verbose --recursive .

server: ## start local mail server (mailhog)
	docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

help: ## show usage and exit
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@sed -nr "/^([a-zA-Z-]+):.*\s##/{s/^([a-zA-Z-]+):.*## (.*)/  \1: \2/;p}" $(MAKEFILE_LIST) | column -c2 -t -s :
