"""Per-run folder layout for scenario reports (txt + html)."""

from __future__ import annotations

from pathlib import Path

_FLOTORCH_DIR = Path(__file__).resolve().parent.parent

# FloTorch/results/<run_id>/report.{txt,html}
RESULTS_ROOT: Path = _FLOTORCH_DIR / "results"


def run_results_dir(run_id: str) -> Path:
    """Return ``FloTorch/results/<run_id>/``, creating it if needed."""
    d = RESULTS_ROOT / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def report_txt_and_html_paths(run_id: str) -> tuple[Path, Path]:
    """Stable filenames inside the run folder."""
    base = run_results_dir(run_id)
    return base / "report.txt", base / "report.html"


def save_scenario_reports(
    run_id: str,
    report_text: str,
    report_html: str,
    *,
    send_email: bool = True,
) -> tuple[Path, Path]:
    """Write report.txt and report.html; optionally email."""
    out_path, html_path = report_txt_and_html_paths(run_id)
    out_path.write_text(report_text, encoding="utf-8")
    html_path.write_text(report_html, encoding="utf-8")
    if send_email:
        from FloTorch.reporting.report_mail import maybe_send_report_email

        maybe_send_report_email(out_path, run_id=run_id, html_body=report_html)
    return out_path, html_path
