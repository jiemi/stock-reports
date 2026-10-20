# Stock Reports

Static GitHub Pages site for published stock reports.

Publish locally. This refreshes the full archive and prints today's links:

    python3 tools/publish_reports.py --date today

Publish, commit, push, and print GitHub Pages links:

    tools/publish_today.sh

Equivalent explicit command:

    python3 tools/publish_reports.py --date today --push

Only generated report files are copied into this repository. Source projects,
databases, cookies, environment files, and other runtime data stay outside this
site.

On this server LeapsStock reports are read from the sibling `LeapsStock/data/reports` directory. Override with `LEAPS_REPORTS_DIR` if needed. Publishing merges local reports into the existing archive and preserves reports from other machines and projects.
