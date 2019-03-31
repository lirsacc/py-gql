#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable
# flake8: noqa
""" Development scripts.

You need ``invoke`` installed to run them.
"""
import os
import sys

import invoke

ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE = "py_gql"


def _join(cmd):
    return " ".join((c for c in cmd if c))


@invoke.task
def deps(ctx, upgrade=False):
    """ Install development dependencies """
    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "pip",
                    "install",
                    "--upgrade" if upgrade else None,
                    "-r dev-requirements.txt",
                ]
            ),
            echo=True,
        )


@invoke.task
def clean(ctx):
    """ Remove test and compilation artifacts """
    with ctx.cd(ROOT):
        ctx.run(
            "find . "
            '| grep -E "(__pycache__|\\.py[cod]|\\.pyo$|\\.so|.pytest_cache|.mypy_cache)" '
            "| xargs rm -rf",
            echo=True,
        )
        ctx.run("rm -rf py_gql/**/*.c  py_gql/*.c", echo=True)
        ctx.run("rm -rf tox .cache htmlcov coverage.xml junit.xml", echo=True)


@invoke.task()
def benchmark(ctx,):
    ctx.run(
        _join(
            [
                "py.test",
                "--benchmark-only",
                "--benchmark-group-by=fullname",
                "tests/benchmarks",
            ]
        ),
        echo=True,
        pty=True,
    )


@invoke.task(iterable=["files", "ignore"])
def test(
    ctx,
    coverage=False,
    bail=True,
    verbose=False,
    grep=None,
    files=None,
    junit=False,
    ignore=None,
):
    """ Run test suite (using: py.test)

    You should be able to run pytest directly but this provides some useful
    shortcuts.
    """

    ignore = ignore or []
    files = ("%s tests" % PACKAGE) if not files else " ".join(files)

    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "py.test",
                    "-c setup.cfg",
                    "--exitfirst" if bail else None,
                    (
                        "--cov %s --cov-config setup.cfg --no-cov-on-fail "
                        "--cov-report term --cov-report html --cov-report xml "
                    )
                    % PACKAGE
                    if coverage
                    else None,
                    "--junit-xml junit.xml" if junit else None,
                    "-vvl --full-trace" if verbose else "-q",
                    "-k %s" % grep if grep else None,
                    (
                        " ".join("--ignore %s" % i for i in ignore)
                        if ignore
                        else None
                    ),
                    files,
                ]
            ),
            echo=True,
            pty=True,
        )


@invoke.task(iterable=["files"])
def flake8(ctx, files=None):
    files = ("%s tests" % PACKAGE) if not files else " ".join(files)
    ctx.run("flake8 %s" % files, echo=True)


@invoke.task(iterable=["files"])
def pylint(ctx, files=None):
    files = ("%s tests" % PACKAGE) if not files else " ".join(files)
    ctx.run(
        "pylint --rcfile=.pylintrc --output-format=colorized -j 0 %s" % files,
        echo=True,
    )


@invoke.task(aliases=["typecheck"], iterable=["files"])
def mypy(ctx, files=None):
    files = ("%s tests" % PACKAGE) if not files else " ".join(files)
    ctx.run("mypy %s" % files, echo=True)


@invoke.task(aliases=["format"], iterable=["files"])
def fmt(ctx, check=False, files=None):
    """ Run formatters """
    files = (
        "%s/**/*.py tests/**/*.py examples/**/*.py" % PACKAGE
        if not files
        else " ".join(files)
    )

    with ctx.cd(ROOT):
        ctx.run(
            _join(["isort", "--check-only" if check else None, files]),
            echo=True,
        )
        # TODO: Track https://github.com/ambv/black/issues/683 for setup.cfg
        # support.
        ctx.run(
            _join(
                [
                    "black",
                    "--line-length=80",
                    "--target-version=py35",
                    "--check" if check else None,
                    files,
                ]
            ),
            echo=True,
        )


@invoke.task
def docs(ctx, clean_=True, strict=False):
    """ Generate documentation """
    with ctx.cd(os.path.join(ROOT, "docs")):
        if clean_:
            ctx.run("rm -rf _build", echo=True)
        ctx.run(
            _join(
                [
                    "sphinx-build",
                    "-W" if strict else None,
                    "-b html",
                    '"." "_build"',
                ]
            ),
            pty=True,
            echo=True,
        )


@invoke.task
def build(ctx):
    """ Build source distribution and wheel for upload to PyPI """
    with ctx.cd(ROOT):
        ctx.run("rm -rf dist", echo=True)
        ctx.run("python setup.py sdist bdist_wheel", echo=True)


ns = invoke.Collection.from_module(sys.modules[__name__])


# Support calling a standalone CLI tool as long as invoke is installed.
if __name__ == "__main__":
    invoke.Program(namespace=ns).run()
