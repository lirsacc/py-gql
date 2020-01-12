#!/bin/bash

cd "$(dirname "$0")" || true

PYTHON_VERSIONS=${PYTHON_VERSIONS:?'PYTHON_VERSIONS must be set.'}
DIST=${1:-'dist'}

for py in $(echo ${PYTHON_VERSIONS//\./} | sed "s/,/ /g"); do

    # Find the correct binary
    pybin=$(ls /opt/python | grep "$py")

    if [ -z "$pybin" ]; then
        echo "No Python installation found for version $py"
        exit 1
    fi

    "/opt/python/${pybin}/bin/python" setup.py bdist_wheel -d "$DIST"

    # Fix wheel
    for whl in "$DIST"/*"${pybin}"*.whl; do
        auditwheel repair "$whl" -w "$DIST"
    done

    # Remove unfixed wheel
    rm -rf "$DIST"/*-"${pybin}"-*linux_*

    # Remove the manylinux1 wheel
    rm -rf "$DIST"/*-"${pybin}"-*manylinux1_*
done
