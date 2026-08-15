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
    assert "new URL(window.location.pathname, window.location.origin)" in switch_handler
    assert "url.searchParams.set('profile', profileSwitch.value)" in switch_handler


def test_shared_layout_has_route_navigation_profile_context_and_skip_link() -> None:
    template = (WEB / "templates" / "base.html").read_text()
    api_source = (WEB.parent / "api.py").read_text()

    assert "{% for key, href, label in nav_items %}" in template
    for route in ("/", "/tenders", "/analytics", "/companies", "/data"):
        assert f'"{route}"' in api_source
    assert 'href="#main-content"' in template
    assert 'id="main-content"' in template
    assert 'aria-label="Основная навигация"' in template
    assert 'aria-current="page"' in template
    assert 'id="profile-switch"' in template
    assert 'id="logout-button"' in template


def test_page_templates_keep_mutation_forms_on_their_owner_pages() -> None:
    templates = {
        name: (WEB / "templates" / name).read_text()
        for name in (
            "overview.html",
            "tenders.html",
            "analytics.html",
            "companies.html",
            "company_detail.html",
            "company_new.html",
            "data.html",
        )
    }

    assert 'id="profile-form"' in templates["company_detail.html"]
    assert 'id="create-profile-form"' in templates["company_new.html"]
    assert 'id="ingestion-form"' in templates["data.html"]
    assert 'id="eis-upload-form"' in templates["data.html"]
    for name in ("overview.html", "tenders.html", "analytics.html", "companies.html"):
        assert 'id="profile-form"' not in templates[name]
        assert 'id="create-profile-form"' not in templates[name]
        assert 'id="ingestion-form"' not in templates[name]


def test_analytics_uses_progressive_disclosure_and_plain_language_history() -> None:
    template = (WEB / "templates" / "analytics.html").read_text()
    stylesheet = (WEB / "static" / "app.css").read_text()

    assert 'class="analytics-primary"' in template
    assert 'class="analytics-secondary"' in template
    assert "Дополнительная аналитика" in template
    assert "История обновлений" in template
    assert "История SCD2" not in template
    assert "@media (max-width: 960px)" not in stylesheet
    assert "@media (max-width: 1080px)" in stylesheet
    assert ".analytics-primary" in stylesheet


def test_company_overview_does_not_offer_operator_data_page() -> None:
    template = (WEB / "templates" / "overview.html").read_text()

    assert "{% if not account %}" in template
    assert 'href="/company"' in template


def test_design_system_defines_focus_responsive_and_reduced_motion_contracts() -> None:
    stylesheet = (WEB / "static" / "app.css").read_text()

    for token in (
        "--color-ink",
        "--color-surface",
        "--color-accent",
        "--space-1",
        "--radius-md",
        "--shadow-sm",
    ):
        assert token in stylesheet
    assert ":focus-visible" in stylesheet
    assert "@media (max-width: 720px)" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
