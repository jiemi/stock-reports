#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


SITE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = SITE_ROOT.parent
TODAY = dt.date.today().isoformat()
DEFAULT_BASE_URL = "https://jiemi.github.io/stock-reports"


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    description: str
    source_dir: Path
    patterns: tuple[str, ...]
    markdown: bool = False


PROJECTS = (
    Project("canslim", "CANSLIM", "CAN SLIM / VCP / pocket pivot strategy reports.", WORKSPACE / "Stock" / "CANSLIM" / "reports", ("*.html",)),
    Project("leapsstock", "LeapsStock", "LEAPS option OI / IV / volume screening daily reports.", WORKSPACE / "Stock" / "LeapsStock" / "data" / "reports", ("*.html",)),
    Project("twitterclaudebot", "TwitterClaudeBot", "X/Twitter finance account stock mention reports.", WORKSPACE / "Stock" / "TwitterClaudeBot" / "reports", ("*.md",), True),
)


@dataclass
class Report:
    project: Project
    title: str
    date_key: str
    source: Path
    output: Path
    href: str


def sh(args: list[str], cwd: Path = SITE_ROOT) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish stock report HTML files to the static site.")
    parser.add_argument("--date", default="today", help="Date to print links for: today, latest, all, or YYYY-MM-DD. The full archive is always refreshed.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Public GitHub Pages base URL, without trailing slash.")
    parser.add_argument("--push", action="store_true", help="Commit and push changes after publishing.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would publish without writing files.")
    return parser.parse_args()


def normalize_date(value: str) -> str:
    if value == "today":
        return TODAY
    if value == "latest":
        return "latest"
    if value == "all":
        return "all"
    dt.date.fromisoformat(value)
    return value


def report_date(path: Path) -> str:
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", path.name)
    if match:
        return match.group(1)
    return dt.date.fromtimestamp(path.stat().st_mtime).isoformat()


def title_from_name(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ")


def inline(text: str) -> str:
    escaped = html.escape(text)
    tick = chr(96)
    escaped = re.sub(tick + r"([^" + tick + r"]+)" + tick, r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) < 2:
        return ""
    out = ["<table>", "<thead><tr>"]
    out.extend(f"<th>{inline(cell)}</th>" for cell in rows[0])
    out.append("</tr></thead><tbody>")
    for row in rows[2:]:
        out.append("<tr>")
        out.extend(f"<td>{inline(cell)}</td>" for cell in row)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def render_markdown(markdown: str, title: str) -> str:
    lines = markdown.splitlines()
    body: list[str] = []
    i = 0
    in_ul = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            if in_ul:
                body.append("</ul>")
                in_ul = False
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= {"-", ":", " "}:
            if in_ul:
                body.append("</ul>")
                in_ul = False
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            body.append(render_table(table_lines))
            continue

        if stripped.startswith("#"):
            if in_ul:
                body.append("</ul>")
                in_ul = False
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            body.append(f"<h{level}>{inline(stripped[level:].strip())}</h{level}>")
        elif stripped.startswith(">"):
            if in_ul:
                body.append("</ul>")
                in_ul = False
            body.append(f"<blockquote>{inline(stripped.lstrip('>').strip())}</blockquote>")
        elif stripped.startswith("- "):
            if not in_ul:
                body.append("<ul>")
                in_ul = True
            body.append(f"<li>{inline(stripped[2:].strip())}</li>")
        else:
            if in_ul:
                body.append("</ul>")
                in_ul = False
            body.append(f"<p>{inline(stripped)}</p>")
        i += 1

    if in_ul:
        body.append("</ul>")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="../../assets/style.css">
  <style>
    main {{ max-width: 1160px; margin: 0 auto; padding: 32px 18px 64px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #dbe3ee; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #edf2f8; }}
    blockquote {{ margin: 12px 0; padding: 10px 14px; background: white; border-left: 4px solid #2563eb; }}
    code {{ background: #edf0f4; border-radius: 4px; padding: 1px 4px; }}
  </style>
</head>
<body><main>
<p class="crumbs"><a href="../../index.html">Reports</a> / {html.escape(title)}</p>
{chr(10).join(body)}
</main></body>
</html>
"""


def clean_generated_dirs() -> None:
    for project in PROJECTS:
        target = SITE_ROOT / project.slug
        if target.exists():
            shutil.rmtree(target)


def collect_reports(dry_run: bool) -> dict[str, list[Report]]:
    reports: dict[str, list[Report]] = {}
    for project in PROJECTS:
        project_reports: list[Report] = []
        if not project.source_dir.exists():
            reports[project.slug] = []
            continue

        sources: list[Path] = []
        for pattern in project.patterns:
            sources.extend(project.source_dir.glob(pattern))

        for source in sorted(set(sources)):
            date_key = report_date(source)
            output_name = f"{source.stem}.html" if project.markdown else source.name
            output = SITE_ROOT / project.slug / "reports" / output_name
            href = f"{project.slug}/reports/{output_name}"
            title = title_from_name(source)
            project_reports.append(Report(project, title, date_key, source, output, href))

            if dry_run:
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            if project.markdown:
                html_doc = render_markdown(source.read_text(encoding="utf-8"), title)
                output.write_text(html_doc, encoding="utf-8")
            else:
                shutil.copy2(source, output)

        reports[project.slug] = sorted(project_reports, key=lambda item: (item.date_key, item.title), reverse=True)
    return reports


def html_page(title: str, body: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
  <main class="shell">
{body}
  </main>
</body>
</html>
"""


def render_project_index(project: Project, project_reports: list[Report]) -> str:
    rows = []
    for report in project_reports:
        rows.append(
            "<tr>"
            f"<td>{html.escape(report.date_key)}</td>"
            f'<td><a href="reports/{html.escape(report.output.name)}">{html.escape(report.title)}</a></td>'
            f"<td>{html.escape(report.output.name)}</td>"
            "</tr>"
        )
    if rows:
        table = '<table class="report-list"><thead><tr><th>日期</th><th>报告</th><th>文件</th></tr></thead><tbody>' + "\n".join(rows) + "</tbody></table>"
    else:
        table = '<div class="empty">还没有发布报告。</div>'
    body = f"""
    <div class="crumbs"><a href="../index.html">首页</a> / {html.escape(project.name)}</div>
    <div class="topbar">
      <div>
        <h1>{html.escape(project.name)}</h1>
        <p class="subtitle">{html.escape(project.description)}</p>
      </div>
      <div class="updated">Updated {html.escape(TODAY)}</div>
    </div>
    <section class="section">
      <h2>报告列表</h2>
      {table}
    </section>
"""
    return html_page(project.name, body, depth=1)


def render_site_index(all_reports: dict[str, list[Report]]) -> str:
    cards = []
    for project in PROJECTS:
        project_reports = all_reports.get(project.slug, [])
        latest = project_reports[0] if project_reports else None
        latest_button = f'<a class="button" href="{html.escape(latest.href)}">最新报告</a>' if latest else '<span class="button secondary">暂无报告</span>'
        latest_meta = html.escape(latest.date_key) if latest else "none"
        cards.append(f"""
      <article class="card">
        <h2>{html.escape(project.name)}</h2>
        <p>{html.escape(project.description)}</p>
        <div class="actions">
          {latest_button}
          <a class="button secondary" href="{html.escape(project.slug)}/index.html">全部报告</a>
        </div>
        <div class="meta">
          <span class="pill">最新：{latest_meta}</span>
          <span class="pill">数量：{len(project_reports)}</span>
        </div>
      </article>
""")

    body = f"""
    <div class="topbar">
      <div>
        <h1>Stock Reports</h1>
        <p class="subtitle">CANSLIM, LeapsStock, and TwitterClaudeBot report archive.</p>
      </div>
      <div class="updated">Updated {html.escape(TODAY)}</div>
    </div>
    <section class="grid">
      {''.join(cards)}
    </section>
"""
    return html_page("Stock Reports", body)


def write_indexes(all_reports: dict[str, list[Report]], dry_run: bool) -> None:
    if dry_run:
        return
    (SITE_ROOT / "index.html").write_text(render_site_index(all_reports), encoding="utf-8")
    for project in PROJECTS:
        project_dir = SITE_ROOT / project.slug
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "index.html").write_text(render_project_index(project, all_reports.get(project.slug, [])), encoding="utf-8")


def ensure_git() -> None:
    if not (SITE_ROOT / ".git").exists():
        sh(["git", "init"])
        sh(["git", "branch", "-M", "main"])


def git_commit_and_push() -> bool:
    ensure_git()
    sh(["git", "add", "."])
    status = sh(["git", "status", "--short"])
    if not status:
        print("No changes to commit.")
        return False
    sh(["git", "commit", "-m", f"Publish reports {TODAY}"])
    remote = sh(["git", "remote"])
    if "origin" not in remote.splitlines():
        raise SystemExit("No git remote named origin. Add one, then rerun with --push.")
    sh(["git", "push", "-u", "origin", "main"])
    return True


def main() -> int:
    args = parse_args()
    link_date = normalize_date(args.date)

    if not args.dry_run:
        ensure_git()
        clean_generated_dirs()

    all_reports = collect_reports(args.dry_run)
    write_indexes(all_reports, args.dry_run)

    if args.push:
        git_commit_and_push()

    base_url = args.base_url.rstrip("/")
    latest_links: list[str] = []
    for project in PROJECTS:
        project_reports = all_reports.get(project.slug, [])
        if not project_reports:
            continue
        selected = project_reports
        if link_date not in {"all", "latest"}:
            selected = [report for report in project_reports if report.date_key == link_date]
        elif link_date == "latest":
            selected = project_reports[:1]

        for report in selected:
            link = f"{base_url}/{report.href}" if base_url else report.href
            latest_links.append(f"{project.name}: {link}")

    print("Published reports:")
    if latest_links:
        print("\n".join(latest_links))
    else:
        print("No matching reports found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
