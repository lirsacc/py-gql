#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""

import itertools
import os

from setuptools import find_packages, setup


NAME = "py_gql"
AUTHOR = "Charles Lirsac"
AUTHOR_EMAIL = "c.lirsac@gmail.com"
URL = "https://github.com/lirsacc/py-gql"

VERSION_TUPLE = (0, 0, 1)
VERSION = ".".join(map(str, VERSION_TUPLE))


def _cython_ext_modules(*globs):
    if bool(os.environ.get("CYTHON_DISABLE")):
        return []

    try:
        from Cython.Build import cythonize
    except ImportError:
        return []
    else:
        linetrace = bool(os.environ.get("CYTHON_TRACE"))
        ext_modules = [
            cythonize(
                glob,
                compiler_directives={
                    "embedsignature": True,
                    "linetrace": linetrace,
                },
            )
            for glob in globs
        ]
        return list(itertools.chain.from_iterable(ext_modules))


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

    version = VERSION

    setup(
        name=NAME,
        version=version,
        description=__doc__.split("\n")[0],
        long_description=readme,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        url=URL,
        license=license_,
        packages=find_packages(exclude=("tests", "docs")),
        install_requires=requirements,
        include_package_data=True,
        ext_modules=_cython_ext_modules(
            "py_gql/*.py",
            "py_gql/lang/*.py",
            "py_gql/validation/*.py",
            "py_gql/utilities/*.py",
            "py_gql/schema/*.py",
            "py_gql/execution/*.py",
        ),
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
