#!/usr/bin/env python
# -*- coding: utf-8 -*-
# mypy: ignore-errors

import glob
import itertools
import os
import sys

import setuptools

_env = os.environ.get

DIR = os.path.abspath(os.path.dirname(__file__))

try:
    sys.pypy_version_info
    PYPY = True
except AttributeError:
    PYPY = False

CYTHON_TRACE = 0

if PYPY or not bool(_env("PY_GQL_USE_CYTHON", False)):
    CYTHON = False
else:
    try:
        from Cython.Build import cythonize
    except ImportError:
        CYTHON = False
    else:
        CYTHON = True
        CYTHON_TRACE = int(_env("CYTHON_TRACE", "0"))


def run_setup():

    pkg = {}

    with open(os.path.join(DIR, "py_gql", "_pkg.py")) as f:
        exec(f.read(), {}, pkg)

    with open(os.path.join(DIR, "README.md")) as f:
        readme = "\n" + f.read()

    setuptools.setup(
        name=pkg["__title__"],
        version=pkg["__version__"],
        description=pkg["__description__"],
        long_description=readme,
        long_description_content_type="text/markdown",
        author=pkg["__author__"],
        author_email=pkg["__author_email__"],
        url=pkg["__url__"],
        license=pkg["__license__"],
        keywords="graphql api",
        zip_safe=False,
        packages=setuptools.find_packages(
            exclude=("tests", "tests.*", "docs", "examples")
        ),
        install_requires=_split_requirements("requirements.txt"),
        tests_require=_split_requirements("test-requirements.txt"),
        include_package_data=True,
        python_requires=">=3.5",
        ext_modules=_ext_modules("py_gql",),
        classifiers=[
            "License :: OSI Approved :: MIT License",
            "Natural Language :: English",
            "Programming Language :: Python",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Operating System :: POSIX",
            "Operating System :: MacOS :: MacOS X",
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Libraries",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
        project_urls={
            "Bug Reports": "%s/issues" % pkg["__url__"],
            "Source": pkg["__url__"],
            "Documentation": "https://py-gql.readthedocs.io/",
        },
    )


def _ext_modules(*packages):
    if not CYTHON:
        return [
            setuptools.Extension(f.replace(".c", "").replace("/", "."), [f])
            for f in itertools.chain.from_iterable(
                glob.iglob("%s/**/*.c" % package, recursive=True)
                for package in packages
            )
        ]

    exts = list(
        itertools.chain.from_iterable(
            (
                cythonize(
                    "%s/**/*.py" % package,
                    compiler_directives={
                        "embedsignature": True,
                        "language_level": 3,
                        "linetrace": CYTHON_TRACE == 1,
                    },
                )
                for package in packages
            )
        )
    )

    if CYTHON_TRACE:
        for ext in exts:
            ext.define_macros.extend([("CYTHON_TRACE", str(CYTHON_TRACE))])

    return exts


def _split_requirements(*requirements_files):
    req = []
    for requirements_file in requirements_files:
        with open(os.path.join(DIR, requirements_file)) as f:
            req.extend(
                [
                    line.strip()
                    for line in f.readlines()
                    if line.strip() and not line.startswith("#")
                ]
            )
    return req


if __name__ == "__main__":
    run_setup()
