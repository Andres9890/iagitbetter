VERSION=$(shell grep -m1 version setup.py | cut -d\' -f2)

.PHONY: help binary clean-pyc clean lint format test install dev-install publish

help:
	@echo "Available targets:"
	@echo "  binary        - Build PEX executable"
	@echo "  clean         - Remove build artifacts and caches"
	@echo "  clean-pyc     - Remove Python file artifacts"
	@echo "  lint          - Run code quality checks (flake8 and black)"
	@echo "  format        - Format code with black"
	@echo "  test          - Run tests with coverage"
	@echo "  install       - Install the package"
	@echo "  dev-install   - Install package in development mode with dev dependencies"
	@echo "  publish       - Tag version and publish to PyPI"

binary:
	pex . --python=python3 --python-shebang='/usr/bin/env python3' -e iagitbetter.__main__:main -o iagitbetter-$(VERSION)-py3-none-any.pex

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean: clean-pyc
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -f *.pex

lint:
	flake8 iagitbetter tests --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 iagitbetter tests --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	black --check iagitbetter tests

format:
	black iagitbetter tests
	isort --profile black --line-length 127 iagitbetter tests

test: clean-pyc
	pytest tests/ -v --cov=iagitbetter --cov-report=xml --cov-report=html --cov-report=term

install:
	pip install .

dev-install:
	pip install -e .
	pip install -r test-requirements.txt

publish: clean
	@echo "Publishing version $(VERSION) to PyPI"
	git tag -a v$(VERSION) -m 'version $(VERSION)'
	git push --tags
	python -m build
	twine upload dist/*
