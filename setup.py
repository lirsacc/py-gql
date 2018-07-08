#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""

from setuptools import find_packages, setup

from py_gql import __pkg__ as pkg


def run_setup():
    with open("README.md") as f:
        readme = "\n" + f.read()

    with open("LICENSE") as f:
        license_ = f.read()

    _requirements = """
    six >= 1.11.0
    futures >= 3.1.1
    """

    requirements = [
        line
        for line in (line.strip() for line in _requirements.split("\n"))
        if line and not line.startswith("#")
    ]

    version = pkg.VERSION

    setup(
        name=pkg.NAME,
        version=version,
        description=__doc__.split("\n")[0],
        long_description=readme,
        author=pkg.pkg.AUTHOR,
        author_email=pkg.AUTHOR_EMAIL,
        url=pkg.URL,
        license=license_,
        packages=find_packages(exclude=("tests", "docs")),
        install_requires=requirements,
        include_package_data=True,
        classifiers=[
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: Implementation :: CPython",
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Libraries",
        ],
    )


if __name__ == "__main__":
    run_setup()
