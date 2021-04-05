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


AUTHOR = ("Charles Lirsac", "c.lirsac@gmail.com")
GITHUB_URL = "https://github.com/lirsacc/py-gql"
SHORT_DESCRIPTION = "Comprehensive GraphQL implementation for Python."


def run_setup():

    with open(os.path.join(DIR, "README.md")) as f:
        readme = "\n" + f.read()

    setuptools.setup(
        name="py_gql",
        version=_get_version(),
        description=SHORT_DESCRIPTION,
        long_description=readme,
        long_description_content_type="text/markdown",
        author=AUTHOR[0],
        author_email=AUTHOR[1],
        url=GITHUB_URL,
        license="MIT",
        keywords="graphql api",
        zip_safe=False,
        packages=setuptools.find_packages(where="src"),
        package_dir={"": "src"},
        install_requires=_split_requirements("requirements.txt"),
        tests_require=_split_requirements("requirements-tests.txt"),
        extras_require={
            "dev": _split_requirements(
                "requirements-dev.txt",
                "requirements-tests.txt",
                "requirements-lint.txt",
                "requirements-mypy.txt",
                "requirements-docs.txt",
            ),
        },
        include_package_data=True,
        python_requires=">=3.6",
        ext_modules=_ext_modules(
            "src/py_gql", exclude=["src/py_gql/schema/_types.py"]
        ),
        classifiers=[
            "License :: OSI Approved :: MIT License",
            "Natural Language :: English",
            "Programming Language :: Python",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3",
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
            "Bug Reports": "%s/issues" % GITHUB_URL,
            "Source": GITHUB_URL,
            "Documentation": "https://py-gql.readthedocs.io/",
        },
    )


def _ext_modules(*packages, exclude=()):
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
                    exclude=exclude,
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
            lines = (line.strip() for line in f.readlines())
            req.extend(
                [
                    line
                    for line in lines
                    if line
                    and not (line.startswith("#") or line.startswith("-"))
                ]
            )
    return req


def _get_version() -> str:
    with open(os.path.join(DIR, "src", "py_gql", "version.py")) as f:
        for line in f.readlines():
            if line.startswith("__version__"):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
        else:
            raise RuntimeError("Unable to find version string.")


if __name__ == "__main__":
    run_setup()
