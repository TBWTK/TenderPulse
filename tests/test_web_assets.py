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
        "description",
        "services",
        "capabilities",
        "keywords",
        "negative_keywords",
        "classifications",
        "countries",
        "customer_types",
        "base_region",
        "service_regions",
        "delivery_mode",
        "excluded_regions",
        "participation_constraints",
        "min_amount",
        "max_amount",
    ):
        assert f"data.get('{field}')" in source


def test_profile_form_does_not_advance_version_before_a_successful_save() -> None:
    source = (WEB / "static" / "app.js").read_text()

    assert "profile.version += 1" not in source
    assert "version: profile.version + 1" in source
    assert "JSON.stringify(update)" in source


def test_company_switch_starts_with_an_unfiltered_recommendation_queue() -> None:
    source = (WEB / "static" / "app.js").read_text()

    switch_handler = source.split("profileSwitch?.addEventListener('change'", maxsplit=1)[1].split(
        "const detailProfileSwitch", maxsplit=1
    )[0]
    assert "new URL('/', window.location.origin)" in switch_handler
    assert "url.searchParams.set('profile', profileSwitch.value)" in switch_handler


def test_sidebar_order_matches_document_order_and_tracks_active_section() -> None:
    template = (WEB / "templates" / "dashboard.html").read_text()
    javascript = (WEB / "static" / "app.js").read_text()
    section_ids = ("opportunities", "analytics", "companies", "loading")

    nav_positions = [template.index(f'href="#{section_id}"') for section_id in section_ids]
    dom_positions = [template.index(f'id="{section_id}"') for section_id in section_ids]

    assert nav_positions == sorted(nav_positions)
    assert dom_positions == sorted(dom_positions)
    assert "IntersectionObserver" in javascript
    assert "aria-current" in javascript
