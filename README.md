# Stock Reports

Static GitHub Pages site for published stock reports.

Publish locally. This refreshes the full archive and prints today's links:

    python3 tools/publish_reports.py --date today

Commit and push after a remote is configured:

    python3 tools/publish_reports.py --date today --push --base-url https://YOUR_USERNAME.github.io/stock-reports

Only generated report files are copied into this repository. Source projects,
databases, cookies, environment files, and other runtime data stay outside this
site.
