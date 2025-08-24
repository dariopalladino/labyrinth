.PHONY: install dev-install test lint format clean build publish help

# Default target
help:
	@echo "Available commands:"
	@echo "  install      Install the package"
	@echo "  dev-install  Install package with development dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black and isort"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  publish      Publish to PyPI"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=labyrinth --cov-report=html --cov-report=term

lint:
	flake8 labyrinth tests examples
	mypy labyrinth
	black --check labyrinth tests examples
	isort --check-only labyrinth tests examples

format:
	black labyrinth tests examples
	isort labyrinth tests examples

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*

# Development workflow targets
setup-dev:
	python -m venv venv
	./venv/bin/pip install --upgrade pip setuptools wheel
	./venv/bin/pip install -e ".[dev]"

check: lint test

ci: setup-dev check
