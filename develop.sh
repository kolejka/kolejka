#!/bin/bash
OFFICE="$(dirname "$(readlink -f "$(which "${0}")")")"
for name in Common Client Observer Worker Foreman Server; do
    pkg="Kolejka${name}"
    pip3 uninstall --yes "${pkg}" >/dev/null 2>&1
    python3 "${OFFICE}/packages/${pkg}/setup.py" develop
done
