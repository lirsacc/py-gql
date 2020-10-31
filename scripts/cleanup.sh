#!/usr/bin/env bash
find src tests -type f -name "*.pyc" -delete
find src tests -type f -name "*.pyo" -delete
find src tests -type f -name "*.pyd" -delete
find src tests -type d -name "__pycache__" -delete
find src tests -type f -name "*.c" -delete
find src tests -type f -name "*.so" -delete
find . src tests -type f -path "*.egg-info*" -delete

if [[ "$*" == *--full* ]] || [[ "$*" == *-f* ]]; then
    rm -rf \
        .pytest_cache \
        .mypy_cache \
        junit*.xml \
        htmlcov* coverage*.xml .coverage* \
        flake8.*

    rm -rf dist build docs/_build
fi
