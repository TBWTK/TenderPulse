from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).parents[1] / "src" / "tenderpulse" / "web"


def test_dashboard_javascript_renders_ai_evidence_without_html_injection() -> None:
    source = (WEB / "static" / "app.js").read_text()

    assert "renderEvidence" in source
    assert "replaceChildren" in source
    assert "textContent" in source
    assert "innerHTML" not in source


def test_dashboard_javascript_projects_every_company_profile_field() -> None:
    source = (WEB / "static" / "app.js").read_text()

    for field in (
        "capabilities",
        "keywords",
        "classifications",
        "countries",
        "min_amount",
        "max_amount",
    ):
        assert f"data.get('{field}')" in source


def test_profile_form_does_not_advance_version_before_a_successful_save() -> None:
    source = (WEB / "static" / "app.js").read_text()

    assert "profile.version += 1" not in source
    assert "version: profile.version + 1" in source
    assert "JSON.stringify(update)" in source
