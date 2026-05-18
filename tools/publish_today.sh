#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 tools/publish_reports.py --date today --push
