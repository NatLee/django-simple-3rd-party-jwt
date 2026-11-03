#!/bin/bash
# Build the sdist the same way the release workflow does (python -m build) and install it,
# a quick way to check what a release would contain.
set -e

rm -rf ./dist
python -m pip install --quiet --upgrade build
python -m build --sdist

pip uninstall -y django-simple-third-party-jwt
python -m pip install ./dist/*.tar.gz
