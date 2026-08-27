#!/usr/bin/env bash
# The deploy build, as a script rather than a one-liner in vercel.json, so it
# can be read and debugged.
#
# Two things make a bare `pip install` unreliable on a build image:
#
#   PEP 668. A modern system Python marks itself externally managed and pip
#   refuses to install into it. A virtualenv sidesteps that entirely.
#
#   `python3` is not guaranteed to be the name. Try the usual ones and say
#   which was found, so a failure names the cause instead of just exiting.
#
# The site build needs Python and Pygments. PyYAML is only used by the
# verifiers, which run in CI and not here.
set -euo pipefail

PY=""
for c in python3 python python3.12 python3.11; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
  echo "vercel_build: no python interpreter on PATH." >&2
  echo "  tried: python3 python python3.12 python3.11" >&2
  echo "  PATH=$PATH" >&2
  exit 1
fi

echo "vercel_build: using $PY ($("$PY" --version 2>&1))"

# A virtualenv rather than the system site-packages, so PEP 668 cannot refuse
# the install and nothing depends on how this image configures pip.
if "$PY" -m venv .vbuild 2>/dev/null; then
  VPY=".vbuild/bin/python"
  [ -x "$VPY" ] || VPY=".vbuild/Scripts/python.exe"
  echo "vercel_build: installing into .vbuild"
  "$VPY" -m pip install --quiet --upgrade pip
  "$VPY" -m pip install --quiet -r requirements.txt
else
  # No venv module. Fall back to a user install, which PEP 668 permits.
  echo "vercel_build: venv unavailable, falling back to --user"
  VPY="$PY"
  "$PY" -m pip install --quiet --user -r requirements.txt
fi

"$VPY" build.py
