#!/usr/bin/env python
# -*- coding: utf-8 -*-
# mypy: ignore-errors
"""
Development scripts.

You need ``invoke`` installed to run them.
"""
import os
import re

import invoke


ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE = "src/py_gql"
DEFAULT_TARGETS = f"{PACKAGE} tests examples"

VALID_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.(dev|a|b|rc)\d+)?$")


def _join(*cmd):
    return " ".join(c for c in cmd if c)


@invoke.task()
def clean(ctx, full=False):
    """
    Remove artifacts and local caches.
    """
    with ctx.cd(ROOT):
        # Delete usual suspects for caching issues.
        ctx.run('find src tests -type f -name "*.pyc" -delete')
        ctx.run('find src tests -type f -name "*.pyo" -delete')
        ctx.run('find src tests -type f -name "*.pyd" -delete')
        ctx.run('find src tests -type d -name "__pycache__" -delete')
        ctx.run('find src tests -type f -name "*.c" -delete')
        ctx.run('find src tests -type f -name "*.so" -delete')
        ctx.run('find . src tests -type f -path "*.egg-info*" -delete')

        if full:
            # These can be useful to keep across test / lint runs so we keep
            # them by default. Pass --full to get as close to a fresh state as
            # possible.
            ctx.run(
                _join(
                    "rm",
                    "-rf ",
                    ".pytest_cache",
                    ".mypy_cache",
                    "junit*.xml",
                    "htmlcov*",
                    "coverage*.xml",
                    ".coverage*",
                    "flake8.*",
                    "dist",
                    "build",
                    "docs/_build",
                ),
            )


@invoke.task(iterable=["files", "ignore"])
def test(
    ctx,
    coverage=False,
    hide_coverage_stats=False,
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
    files = f"{PACKAGE} tests" if not files else " ".join(files)

    with ctx.cd(ROOT):
        ctx.run(
            _join(
                "py.test",
                "-c setup.cfg",
                "--exitfirst" if bail else None,
                (
                    f"--cov {PACKAGE} --cov-config setup.cfg --no-cov-on-fail"
                    if coverage
                    else None
                ),
                "--cov-report=" if coverage and hide_coverage_stats else None,
                "--junit-xml junit.xml" if junit else None,
                "--looponfail" if watch else None,
                "-vvl --full-trace" if verbose else "-q",
                "-rf",
                f"-k {grep}" if grep else None,
                "-n auto" if parallel else None,
                " ".join(f"--ignore {i}" for i in ignore) if ignore else None,
                files,
            ),
            echo=True,
            pty=True,
        )


@invoke.task(aliases=["bench"])
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


@invoke.task(iterable=["files"])
def flake8(ctx, files=None, junit=False):
    files = f"{DEFAULT_TARGETS} setup.py" if not files else " ".join(files)
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
    files = f"{PACKAGE} tests" if not files else " ".join(files)
    ctx.run(
        _join("mypy", "--junit-xml mypy.junit.xml" if junit else None, files),
        echo=True,
    )


@invoke.task(aliases=["format"], iterable=["files"])
def fmt(ctx, files=None):
    """
    Run formatters.
    """
    targets = (
        f"{DEFAULT_TARGETS} setup.py tasks.py" if not files else " ".join(files)
    )
    with ctx.cd(ROOT):
        ctx.run(_join("isort", targets), echo=True)
        ctx.run(_join("black", targets), echo=True)


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
        python_versions = "36,37,38,39"
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
                f"-e PYTHON_VERSIONS={python_versions}",
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
                f"Invalid version format, must match /{VALID_VERSION_RE.pattern}/.",
            )

        pkg = {}

        with open(os.path.join(PACKAGE, "version.py")) as f:
            exec(f.read(), {}, pkg)

        local_version = pkg["__version__"]

        if (not force) and local_version >= version:
            raise invoke.exceptions.Exit(
                f"Must increment the version (current {local_version}).",
            )

        with open(os.path.join(PACKAGE, "version.py")) as f:
            new_file = f.read().replace(local_version, version)

        with open(os.path.join(PACKAGE, "version.py"), "w") as f:
            f.write(new_file)

        modified = ctx.run("git ls-files -m", hide=True)

        if (not force) and modified.stdout.strip() != f"{PACKAGE}/version.py":
            raise invoke.exceptions.Exit(
                "There are still modified files in your directory. "
                "Commit or stash them.",
            )

        ctx.run(f"git add {PACKAGE}/version.py")
        ctx.run(f"git commit -m v{version}")
        ctx.run(f"git tag v{version}")

        if push:
            ctx.run("git push && git push --tags")
