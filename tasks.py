# -*- coding: utf-8 -*-
import os

import invoke

import setup as pkg

ROOT = os.path.dirname(os.path.abspath(__file__))


def _join(cmd):
    return " ".join((c for c in cmd if c))


@invoke.task
def deps(ctx):
    """ Install dependencies """
    with ctx.cd(ROOT):
        ctx.run("pip install -r dev-requirements.txt", echo=True)


@invoke.task
def clean(ctx):
    """ Remove test and compilation artifacts """
    with ctx.cd(ROOT):
        ctx.run(
            "find . "
            '| grep -E "(__pycache__|\\.py[cod]|\\.pyo$|\\.so|\\.c|.pytest_cache)" '
            "| xargs rm -rf",
            echo=True,
        )
        ctx.run("rm -rf tox .cache htmlcov coverage.xml junit.xml", echo=True)


@invoke.task
def test(
    ctx,
    coverage=False,
    bail=True,
    verbose=False,
    grep=None,
    file_=None,
    junit=False,
):
    """ Run test suite (using: py.test) """
    with ctx.cd(ROOT):
        ctx.run(
            _join(
                [
                    "py.test",
                    "-c test.ini",
                    "--color yes",
                    "--doctest-modules --doctest-continue-on-failure",
                    "--exitfirst" if bail else None,
                    (
                        "--cov %s --cov-config test.ini --no-cov-on-fail "
                        "--cov-report term --cov-report html --cov-report xml "
                        % pkg.NAME
                    )
                    if coverage
                    else None,
                    "--junit-xml junit.xml" if junit else None,
                    "-vvl --full-trace" if verbose else "--quiet",
                    "-k %s" % grep if grep else None,
                    "%s tests" % pkg.NAME if file_ is None else file_,
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
                    "tox -c test.ini",
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
def lint(ctx, pylint=True):
    """ Run flake8 linter """
    with ctx.cd(ROOT):
        ctx.run("flake8 --config .flake8 %s tests" % pkg.NAME, echo=True)
        if pylint:
            ctx.run(
                _join(
                    [
                        "pylint",
                        "--rcfile=.pylintrc",
                        "--output-format=colorized",
                        "%s tests" % pkg.NAME,
                    ]
                ),
                echo=True,
            )


@invoke.task
def fmt(ctx, verbose=False, files=None):
    """ Run the black https://github.com/ambv/black formatter """
    with ctx.cd(ROOT):
        ctx.run(
            "isort --multi-line=3 --trailing-comma --force-grid-wrap=0 "
            "--combine-as --apply --line-width=80 "
            "py_gql/**/*.py tests/**/*.py",
            echo=True,
        )
        ctx.run(
            "black --line-length=80 py_gql/**/*.py tests/**/*/*.py", echo=True
        )


@invoke.task
def docs(ctx, clean=True, regenerate_reference=False, strict=False):
    """ Generate documentation """
    with ctx.cd(os.path.join(ROOT, "docs")):
        if clean:
            ctx.run("rm -rf _build", echo=True)
        if regenerate_reference:
            if clean:
                ctx.run("rm -rf ref", echo=True)
            ctx.run(
                "sphinx-apidoc -Mef -o ref ../%s" % pkg.NAME,
                pty=True,
                echo=True,
            )
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
