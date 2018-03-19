# -*- coding: utf-8 -*-
""" """

import contextlib
import os
import invoke

from setup import PKG_NAME


ROOT = os.path.dirname(os.path.abspath(__file__))


def _join(cmd):
    return ' '.join((c for c in cmd if c))


@contextlib.contextmanager
def _root_dir():
    current = os.getcwd()
    os.chdir(ROOT)
    yield
    os.chdir(current)


@invoke.task
def deps(ctx):
    """ Install dependencies """
    with _root_dir():
        ctx.run('pip install -r dev-requirements.txt', echo=True)


@invoke.task
def clean(ctx):
    """ Remove test and compilation artifacts """
    ctx.run(
        'find . '
        '| grep -E "(__pycache__|\.py[cod]|\.pyo$|\.so)" '
        '| xargs rm -rf',
        echo=True
    )
    ctx.run('rm -rf tox .cache htmlcov coverage.xml', echo=True)


@invoke.task
def test(ctx, coverage=False, bail=True, verbose=False, grep=None):
    """ Run test suite (using: py.test) """
    cmd = [
        'py.test --color=yes --doctest-modules',
        '--exitfirst' if bail else None,
        ('--cov %s '
         '--cov-report term-missing '
         '--cov-report html '
         '--cov-report xml '
         '--no-cov-on-fail' % PKG_NAME) if coverage else None,
        '-vvl --full-trace' if verbose else None,
        '-k %s' % grep if grep else None,
        '%s' % PKG_NAME,
        'tests',
    ]
    with _root_dir():
        ctx.run(_join(cmd), echo=True, pty=True)


@invoke.task(name='tox', aliases=['test.tox'])
def tox(ctx, rebuild=False, hashseed=None, strict=False, envlist=None):
    """ Run test suite against multiple python versions (using: tox) """
    cmd = [
        'tox -c test.ini',
        '--recreate' if rebuild else None,
        '--hashseed %s' % hashseed if hashseed is not None else None,
        '--envlist %s' % envlist if envlist is not None else None,
        '--skip-missing-interpreters' if strict else None,
    ]
    with _root_dir():
        ctx.run(_join(cmd), echo=True, pty=True)


@invoke.task
def lint(ctx, verbose=False):
    with _root_dir():
        ctx.run(_join([
            'flake8',
            '--config .flake8',
            '--show-source' if verbose else None,
            '%s tests' % PKG_NAME,
        ]), echo=True)
