from __future__ import annotations

import datetime as _dt
import html
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


def _sanitize_name(nodeid: str) -> str:
    """Convert a pytest node id into a filename-safe slug."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nodeid)


@dataclass
class TestResult:
    nodeid: str
    outcome: str
    duration: float
    screenshot: str | None
    message: str | None


class TestRunReporter:
    """
    Collect per-test results and produce a timestamped HTML report (with screenshots).
    A new report directory is created under ./reports/ for each test run.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[1]
        self.run_started_at = _dt.datetime.now()
        ts = self.run_started_at.strftime("%Y-%m-%d_%H-%M-%S")

        self.run_dir = self.repo_root / "reports" / ts
        self.screenshots_dir = self.run_dir / "screenshots"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)

        self.results: list[TestResult] = []
        self.report_path: Path | None = None

    def record(self, item: Any, report: Any, driver: Any | None, *, stage: str) -> None:
        """
        Store a test outcome for a given stage (setup/call/teardown) and capture a
        screenshot on the call stage if a driver is available. If a later stage fails,
        the existing record is updated so teardown failures still surface.
        """
        status = self._status_for(report)
        message = self._message_for(report)
        props_text = self._props_text(report)

        existing_idx = self._result_index(item.nodeid)
        existing = self.results[existing_idx] if existing_idx is not None else None

        screenshot_rel: str | None = existing.screenshot if existing else None
        screenshot_error: str | None = None

        if stage == "call" and driver is not None:
            safe_name = _sanitize_name(item.nodeid)
            screenshot_path = self.screenshots_dir / f"{safe_name}.png"
            try:
                success = driver.save_screenshot(str(screenshot_path))
                if success:
                    screenshot_rel = str(screenshot_path.relative_to(self.run_dir))
                else:
                    screenshot_error = "save_screenshot returned False"
            except Exception as exc:  # pragma: no cover - best effort logging
                screenshot_error = f"Screenshot failed: {exc}"

        if screenshot_error:
            message = f"{message or ''}\n(Screenshot error: {screenshot_error})".strip()
        if message is None and existing and existing.message:
            message = existing.message
        if props_text:
            message = f"{message + '\n' if message else ''}{props_text}".strip()

        duration = getattr(report, "duration", 0.0) or 0.0
        if existing and stage != "call":
            duration = existing.duration or duration

        result = TestResult(
            nodeid=item.nodeid,
            outcome=status,
            duration=duration,
            screenshot=screenshot_rel,
            message=message or None,
        )

        if existing_idx is None:
            self.results.append(result)
        else:
            self.results[existing_idx] = result

    def finalize(self) -> Path:
        """
        Write the HTML and JSON reports. Idempotent to avoid duplicate writes.
        """
        if self.report_path is not None and self.report_path.exists():
            return self.report_path

        self.report_path = self.run_dir / "report.html"
        self._write_json()
        self._write_html()
        return self.report_path

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _status_for(self, report: Any) -> str:
        status = getattr(report, "outcome", "unknown")
        was_xfail = getattr(report, "wasxfail", False)
        if was_xfail:
            return "xfailed" if getattr(report, "failed", False) else "xpassed"
        return status

    def _message_for(self, report: Any) -> str | None:
        if getattr(report, "failed", False) or getattr(report, "skipped", False):
            text = getattr(report, "longreprtext", "") or ""
            return text.strip() if text else None
        return None

    def _props_text(self, report: Any) -> str:
        props = getattr(report, "user_properties", None) or []
        lines = []
        for key, value in props:
            try:
                val_str = json.dumps(value, indent=2, default=str)
            except TypeError:
                val_str = repr(value)
            lines.append(f"{key}: {val_str}")
        return "\n".join(lines)

    def _result_index(self, nodeid: str) -> int | None:
        for idx, res in enumerate(self.results):
            if res.nodeid == nodeid:
                return idx
        return None

    def _write_json(self) -> None:
        payload = {
            "started_at": self.run_started_at.isoformat(),
            "finished_at": _dt.datetime.now().isoformat(),
            "results": [asdict(r) for r in self.results],
        }
        json_path = self.run_dir / "report.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_html(self) -> None:
        total = len(self.results)
        summary = {
            "passed": sum(1 for r in self.results if r.outcome == "passed"),
            "failed": sum(1 for r in self.results if r.outcome == "failed"),
            "skipped": sum(1 for r in self.results if r.outcome == "skipped"),
            "xfailed": sum(1 for r in self.results if r.outcome == "xfailed"),
            "xpassed": sum(1 for r in self.results if r.outcome == "xpassed"),
        }

        rows = []
        for res in self.results:
            msg_html = (
                f"<pre>{html.escape(res.message)}</pre>" if res.message else "<span class='muted'>—</span>"
            )
            if res.screenshot:
                screenshot_html = (
                    f"<a href='{html.escape(res.screenshot)}' target='_blank'>"
                    f"<img src='{html.escape(res.screenshot)}' alt='screenshot for {html.escape(res.nodeid)}' />"
                    "</a>"
                )
            else:
                screenshot_html = "<span class='muted'>n/a</span>"

            rows.append(
                "<tr class='status-{status}'>"
                "<td class='test'>{test}</td>"
                "<td class='status'>{status}</td>"
                "<td class='duration'>{duration:.2f}s</td>"
                "<td class='screenshot'>{shot}</td>"
                "<td class='message'>{message}</td>"
                "</tr>".format(
                    status=html.escape(res.outcome),
                    test=html.escape(res.nodeid),
                    duration=res.duration,
                    shot=screenshot_html,
                    message=msg_html,
                )
            )

        rows_html = "\n".join(rows) if rows else "<tr><td colspan='5' class='muted'>No tests collected.</td></tr>"

        finished_at = _dt.datetime.now()

        html_body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>WP Selenium Test Report - {self.run_started_at:%Y-%m-%d %H:%M:%S}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
    h1 {{ margin-bottom: 0; }}
    .meta {{ color: #666; margin-top: 4px; }}
    .summary {{ display: flex; gap: 12px; margin: 16px 0; flex-wrap: wrap; }}
    .pill {{ padding: 6px 10px; border-radius: 14px; font-weight: 600; font-size: 14px; }}
    .passed {{ background: #e6ffed; color: #18794e; }}
    .failed {{ background: #ffe8e6; color: #c52727; }}
    .skipped {{ background: #f5f5f5; color: #444; }}
    .xfailed {{ background: #f5f5f5; color: #444; }}
    .xpassed {{ background: #fff4db; color: #946200; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f8f8f8; text-align: left; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    tr.status-failed {{ background: #fff4f4; }}
    tr.status-passed {{ background: #f7fffa; }}
    td.status {{ font-weight: 700; width: 90px; }}
    td.duration {{ width: 90px; white-space: nowrap; }}
    td.screenshot img {{ max-width: 320px; border: 1px solid #ccc; border-radius: 4px; }}
    pre {{ white-space: pre-wrap; margin: 0; font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace; }}
    .muted {{ color: #777; }}
  </style>
</head>
<body>
  <h1>WP Selenium Test Report</h1>
  <div class="meta">
    Started: {self.run_started_at:%Y-%m-%d %H:%M:%S} ·
    Finished: {finished_at:%Y-%m-%d %H:%M:%S} ·
    Run folder: {html.escape(str(self.run_dir.relative_to(self.repo_root)))}
  </div>

  <div class="summary">
    <div class="pill passed">Passed: {summary['passed']}</div>
    <div class="pill failed">Failed: {summary['failed']}</div>
    <div class="pill skipped">Skipped: {summary['skipped']}</div>
    <div class="pill xfailed">XFailed: {summary['xfailed']}</div>
    <div class="pill xpassed">XPassed: {summary['xpassed']}</div>
    <div class="pill" style="background:#eef2ff;color:#1f3a93;">Total: {total}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Test</th>
        <th>Status</th>
        <th>Duration</th>
        <th>Screenshot</th>
        <th>Details</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>
"""

        assert self.report_path is not None
        self.report_path.write_text(html_body, encoding="utf-8")
