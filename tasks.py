#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
def clean(ctx, include_cython_files=False):
    """ Remove test and compilation artifacts """
    with ctx.cd(ROOT):
        ctx.run(
            "find . "
            '| grep -E "(__pycache__|\\.py[cod]|\\.pyo$|.pytest_cache|.mypy_cache)$" '
            "| xargs rm -rf",
            echo=True,
        )
        ctx.run("rm -rf tox .cache htmlcov coverage.xml junit.xml", echo=True)

        if include_cython_files:
            ctx.run(
                'find %s | grep -E "(\\.c|\\.so)$" | xargs rm -rf' % PACKAGE,
                echo=True,
            )


@invoke.task()
def benchmark(ctx,):
    """ Run benchmarks. """
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
    parallel=False,
):
    """ Run test suite (using: py.test)

    You should be able to run pytest directly but this provides some useful
    shortcuts and defaults.
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
                    "-n auto" if parallel else None,
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
def flake8(ctx, files=None, junit=False):
    files = ("%s tests" % PACKAGE) if not files else " ".join(files)
    try:
        ctx.run(
            _join(
                [
                    "flake8",
                    "--output-file flake8.txt --tee" if junit else None,
                    files,
                ]
            ),
            echo=True,
        )
    except invoke.exceptions.UnexpectedExit as err:
        raise
    finally:
        if junit:
            ctx.run("flake8_junit flake8.txt flake8.junit.xml", echo=True)


@invoke.task(aliases=["typecheck"], iterable=["files"])
def mypy(ctx, files=None, junit=False):
    files = ("%s tests" % PACKAGE) if not files else " ".join(files)
    ctx.run(
        _join(["mypy", "--junit-xml mypy.junit.xml" if junit else None, files]),
        echo=True,
    )


@invoke.task(iterable=["files"])
def sort_imports(ctx, check=False, files=None):
    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "isort",
                    (
                        "-rc %s tests examples setup.py tasks.py" % PACKAGE
                        if not files
                        else " ".join(files)
                    ),
                    "--check-only" if check else None,
                ]
            ),
            echo=True,
        )


@invoke.task(iterable=["files"])
def black(ctx, check=False, files=None):
    ctx.run(
        _join(
            [
                "black",
                "--check" if check else None,
                (
                    "%s tests examples setup.py tasks.py" % PACKAGE
                    if not files
                    else " ".join(files)
                ),
            ]
        ),
        echo=True,
    )


@invoke.task(aliases=["format"], iterable=["files"])
def fmt(ctx, files=None):
    """ Run formatters """
    with ctx.cd(ROOT):
        sort_imports(ctx, files=files)
        black(ctx, files=files)


@invoke.task(pre=[invoke.call(black, check=True), flake8, mypy, test])
def check(ctx):
    """ Run all checks. """
    pass


@invoke.task
def docs(ctx, clean_=True, strict=False, verbose=False):
    """ Generate documentation """
    with ctx.cd(os.path.join(ROOT, "docs")):
        if clean_:
            ctx.run("rm -rf _build", echo=True)

        ctx.run(
            _join(
                [
                    "sphinx-build",
                    "-v" if verbose else "",
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
