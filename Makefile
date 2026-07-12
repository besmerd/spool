.PHONY: install test coverage lint docs build clean server

PYTHON := python3.12
VENV := .venv
BIN := $(VENV)/bin

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip

install: $(BIN)/python ## install development dependencies
	$(BIN)/python -m pip install --editable '.[test,lint,docs,release]'

test: ## run the test suite
	$(BIN)/python -m pytest

coverage: ## run tests with coverage
	$(BIN)/python -m coverage run -m pytest
	$(BIN)/python -m coverage report

lint: ## run the Python linter
	$(BIN)/python -m pylint spool

docs: ## build the documentation
	$(BIN)/python -m mkdocs build

build: ## build wheel and source distributions
	$(BIN)/python -m build

clean: ## remove generated artifacts
	rm -rf build dist site htmlcov *.egg-info
	rm -f .coverage coverage.xml

server: ## start a local MailHog server
	docker run -d -p 1025:1025 -p 8025:8025 --name mailhog mailhog/mailhog
