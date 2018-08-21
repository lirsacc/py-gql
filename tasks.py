# -*- coding: utf-8 -*-
import os
import sys

import invoke

ROOT = os.path.dirname(os.path.abspath(__file__))
PKG = "py_gql"


def _join(cmd):
    return " ".join((c for c in cmd if c))


@invoke.task
def deps(ctx, upgrade=False):
    """ Install dependencies """
    requirements = (
        "dev-requirements.txt"
        if sys.version >= "3"
        else "py2-dev-requirements.txt"
    )
    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "CYTHON_DISABLE=1",
                    "pip",
                    "install",
                    "--upgrade" if upgrade else None,
                    "-r %s" % requirements,
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
            '| grep -E "(__pycache__|\\.py[cod]|\\.pyo$|\\.so|.pytest_cache)" '
            "| xargs rm -rf",
            echo=True,
        )
        ctx.run("rm -rf py_gql/**/*.c  py_gql/*.c", echo=True)
        ctx.run("rm -rf tox .cache htmlcov coverage.xml junit.xml", echo=True)


@invoke.task
def test(
    ctx,
    coverage=False,
    bail=True,
    verbose=False,
    grep=None,
    files=None,
    junit=False,
):
    """ Run test suite (using: py.test) """

    ignore = []
    if sys.version < "3.5":
        ignore.extend(["py_gql/asyncio.py", "tests/test_asyncio.py"])

    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "py.test",
                    "-c pytest.ini",
                    "--exitfirst" if bail else None,
                    (
                        "--cov %s --cov-config pytest.ini --no-cov-on-fail "
                        "--cov-report term --cov-report html --cov-report xml "
                        % PKG
                    )
                    if coverage
                    else None,
                    "--junit-xml junit.xml" if junit else None,
                    "-vvl --full-trace" if verbose else None,
                    "-k %s" % grep if grep else None,
                    (
                        " ".join("--ignore %s" % i for i in ignore)
                        if ignore
                        else None
                    ),
                    "%s tests" % PKG if files is None else files,
                ]
            ),
            echo=True,
            pty=True,
        )


@invoke.task(name="tox", aliases=["test.tox"])
def tox(ctx, rebuild=False, hashseed=None, strict=False, envlist=None):
    """ Run test suite against multiple python versions (using: tox) """
    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "tox -c tox.ini",
                    "--recreate" if rebuild else None,
                    "--hashseed %s" % hashseed
                    if hashseed is not None
                    else None,
                    "-e %s" % envlist if envlist is not None else None,
                    "--skip-missing-interpreters" if strict else None,
                ]
            ),
            echo=True,
            pty=True,
        )


@invoke.task
def lint(ctx, pylint=True, flake8=True, files=None):
    """ Run linters """

    if files is None:
        files = "%s tests" % PKG

    with ctx.cd(ROOT):
        if flake8:
            ctx.run("flake8 --config .flake8 %s" % files, echo=True)

        if pylint:
            ctx.run(
                _join(
                    [
                        "pylint",
                        "--rcfile=.pylintrc",
                        "--output-format=colorized",
                        "--jobs=0",
                        files,
                    ]
                ),
                echo=True,
            )


@invoke.task
def fmt(ctx, files=None):
    """ Run formatters """

    if files is None:
        files = "%s/**/*.py tests/**/*.py examples/**/*.py" % PKG

    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "isort",
                    "--multi-line=3",
                    "--trailing-comma",
                    "--force-grid-wrap=0",
                    "--combine-as",
                    "--apply",
                    "--line-width=80",
                    "-ns __init__.py",
                    files,
                ]
            ),
            echo=True,
        )

        ctx.run(_join(["black", "--line-length=80", files]), echo=True)


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
