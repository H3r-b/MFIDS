#!/usr/bin/env bash
# exit on error
set -o errexit

poetry install --with mfids-site --no-root

python authsysproject/manage.py collectstatic --no-input
python authsysproject/manage.py migrate