#!/usr/bin/env python
# -*- coding: utf-8 -*-
# mypy: ignore-errors
"""
Development scripts.

You need ``invoke`` installed to run them.
"""
import os
import re
import sys

import invoke


ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE = "src/py_gql"
DEFAULT_TARGETS = (
    "%s tests examples" % PACKAGE
    if sys.version >= "3.6"
    else "%s tests" % PACKAGE
)

VALID_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.(dev|a|b|rc)\d+)?$")


def _join(*cmd):
    return " ".join(c for c in cmd if c)


@invoke.task()
def benchmark(ctx):
    """
    Run benchmarks.
    """
    with ctx.cd(ROOT):
        ctx.run(
            _join(
                "py.test",
                "--benchmark-only",
                "--benchmark-group-by=fullname",
                "tests/benchmarks",
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
    watch=False,
):
    """
    Run test suite (using: py.test).

    You should be able to run pytest directly but this provides some useful
    shortcuts and defaults.
    """
    ignore = ignore or []
    files = ("%s tests" % PACKAGE) if not files else " ".join(files)

    with ctx.cd(ROOT):
        ctx.run(
            _join(
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
                "--looponfail" if watch else None,
                "-vvl --full-trace" if verbose else "-q",
                "-rf",
                "-k %s" % grep if grep else None,
                "-n auto" if parallel else None,
                (
                    " ".join("--ignore %s" % i for i in ignore)
                    if ignore
                    else None
                ),
                files,
            ),
            echo=True,
            pty=True,
        )


@invoke.task(iterable=["files"])
def flake8(ctx, files=None, junit=False):
    files = DEFAULT_TARGETS if not files else " ".join(files)
    try:
        ctx.run(
            _join(
                "flake8",
                "--output-file flake8.txt --tee" if junit else None,
                files,
            ),
            echo=True,
        )
    except invoke.exceptions.UnexpectedExit:
        raise
    finally:
        if junit:
            ctx.run("flake8_junit flake8.txt flake8.junit.xml", echo=True)


@invoke.task(aliases=["typecheck"], iterable=["files"])
def mypy(ctx, files=None, junit=False):
    files = DEFAULT_TARGETS if not files else " ".join(files)
    ctx.run(
        _join("mypy", "--junit-xml mypy.junit.xml" if junit else None, files),
        echo=True,
    )


@invoke.task(aliases=["format"], iterable=["files"])
def fmt(ctx, files=None):
    """
    Run formatters.
    """
    with ctx.cd(ROOT):
        ctx.run(
            _join(
                "isort",
                (
                    "-rc %s setup.py tasks.py" % DEFAULT_TARGETS
                    if not files
                    else " ".join(files)
                ),
            ),
            echo=True,
        )
        ctx.run(
            _join(
                "black",
                (
                    "%s setup.py tasks.py" % DEFAULT_TARGETS
                    if not files
                    else " ".join(files)
                ),
            ),
            echo=True,
        )


@invoke.task(pre=[flake8, mypy, test])
def check(ctx):
    """
    Run all checks (formatting, lint, typecheck and tests).
    """
    with ctx.cd(ROOT):
        pass


@invoke.task
def docs(ctx, clean_=False, strict=False, verbose=False):
    """
    Generate documentation.
    """
    with ctx.cd(os.path.join(ROOT, "docs")):
        if clean_:
            ctx.run("rm -rf _build", echo=True)

        ctx.run(
            _join(
                "sphinx-build",
                "-v" if verbose else "",
                "-W" if strict else None,
                "-b html",
                '"." "_build"',
            ),
            pty=True,
            echo=True,
        )


@invoke.task
def build(ctx, cythonize_module=False):
    """
    Build source distribution and wheel.
    """
    with ctx.cd(ROOT):
        ctx.run("rm -rf dist", echo=True)
        ctx.run(
            _join(
                "PY_GQL_USE_CYTHON=1" if cythonize_module else None,
                "python",
                "setup.py",
                "sdist",
                "bdist_wheel",
            ),
            echo=True,
        )


@invoke.task(iterable=["python"])
def build_manylinux_wheels(ctx, python, cythonize_module=True, all_=False):
    """
    Build and extract a manylinux wheel using the official docker image.

    See https://github.com/pypa/manylinux for more information.
    """
    if not python and not all_:
        raise invoke.exceptions.Exit("Must define at least one Python version.")

    if all_:
        python_versions = "35,36,37,38,39"
    else:
        python_versions = ",".join(python)

    with ctx.cd(ROOT):
        ctx.run(
            _join(
                "docker",
                "run",
                "--rm",
                "-v $(pwd):/workspace",
                "-w /workspace",
                "-e PYTHON_VERSIONS=%s" % python_versions,
                "-e PY_GQL_USE_CYTHON=1" if cythonize_module else None,
                "quay.io/pypa/manylinux2010_x86_64",
                "bash -c /workspace/scripts/build-manylinux-wheels.sh",
            ),
            echo=True,
        )


@invoke.task
def generate_checksums(ctx):
    with ctx.cd(os.path.join(ROOT, "dist")):
        ctx.run("rm -rf checksums.txt")
        ctx.run(
            'find . -name "*%s*" -type f -exec sha256sum "{}" + >| checksums.txt'
            % PACKAGE,
            echo=True,
        )


@invoke.task
def update_version(ctx, version, force=False, push=False):
    """
    Update version and create relevant git tag.
    """
    with ctx.cd(ROOT):
        if not VALID_VERSION_RE.match(version):
            raise invoke.exceptions.Exit(
                "Invalid version format, must match /%s/."
                % VALID_VERSION_RE.pattern
            )

        pkg = {}

        with open(os.path.join(PACKAGE, "_pkg.py")) as f:
            exec(f.read(), {}, pkg)

        local_version = pkg["__version__"]

        if (not force) and local_version >= version:
            raise invoke.exceptions.Exit(
                "Must increment the version (current %s)." % local_version
            )

        with open(os.path.join(PACKAGE, "_pkg.py")) as f:
            new_file = f.read().replace(local_version, version)

        with open(os.path.join(PACKAGE, "_pkg.py"), "w") as f:
            f.write(new_file)

        modified = ctx.run("git ls-files -m", hide=True)

        if (not force) and modified.stdout.strip() != "%s/_pkg.py" % PACKAGE:
            raise invoke.exceptions.Exit(
                "There are still modified files in your directory. "
                "Commit or stash them."
            )

        ctx.run("git add %s/_pkg.py" % PACKAGE)
        ctx.run("git commit -m v%s" % version)
        ctx.run("git tag v%s" % version)

        if push:
            ctx.run("git push && git push --tags")
