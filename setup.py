#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint:disable=all
"""
"""

import itertools
import os
import sys

from setuptools import find_packages, setup


def run_setup():

    about = {}
    with open(os.path.join("py_gql", "__version__.py")) as f:
        exec(f.read(), about)

    with open("README.md") as f:
        readme = "\n" + f.read()

    setup(
        name=about["__title__"],
        version=about["__version__"],
        description=about["__description__"],
        long_description=readme,
        long_description_content_type="text/markdown",
        author=about["__author__"],
        author_email=about["__author_email__"],
        url=about["__url__"],
        license=about["__license__"],
        zip_safe=False,
        packages=find_packages(exclude=("tests", "docs", "examples")),
        # package_data={},
        install_requires=_split_requirements("requirements.txt"),
        include_package_data=True,
        python_requires=">=2.6, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
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
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: Implementation :: CPython",
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Libraries",
        ],
        tests_require=(
            _split_requirements(
                "test-requirements.txt", "py3-test-requirements.txt"
            )
            if sys.version >= "3"
            else _split_requirements("test-requirements.txt")
        ),
    )


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


def _split_requirements(*requirements_files):
    req = []
    for requirements_file in requirements_files:
        with open(requirements_file) as f:
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
