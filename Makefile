SHELL := /bin/sh
PYTHON_VERSION := python3

PROJECT := mailman
VIRTUAL_ENV := venv
PYTHON_BIN := $(VIRTUAL_ENV)/bin

.DEFAULT: help

.PHONY: help
help:
	@echo "clean"
	@echo "    remove all build, test, coverage and Python artifacts"
	@echo "install"
	@echo "    install package and dependencies to local virtual environment"
	@echo "coverage"
	@echo "    run code coverage"
	@echo "test"
	@echo "    run test suite"
	@echo "isort"
	@echo "    sort package imports"
	@echo "server"
	@echo "    start local mailserver (mailhog)"

venv/bin/activate:
	test -d venv || $(PYTHON_VERSION) -m venv $(VIRTUAL_ENV)
	$(PYTHON_BIN)/python -m pip install --upgrade pip
	touch venv/bin/activate

venv: venv/bin/activate

.PHONY: install
install: venv
	$(PYTHON_BIN)/python -m pip install --editable .

.PHONY: clean
clean: clean-build clean-pyc clean-test

.PHONY: clean-build
clean-build:
	rm -rf .eggs/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name '*.egg' -delete

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.py[co]' -delete
	find . -name '*~'  -delete
	find . -name '__pycache__'  -delete

.PHONY: clean-test
clean-test:
	rm -f .coverage
	rm -rf .tox/
	rm -rf htmlcov/

.PHONY: test
test:
	-tox

.PHONY: lint
lint:
	-tox -e lint

.PHONY: coverage
coverage: test
	coverage report
	coverage html
	cd htmlcov && python -m http.server

.PHONY: isort
isort:
	isort --verbose --recursive .

.PHONY: server
server:
	docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
