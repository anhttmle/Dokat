"""Unit tests for route registry and matcher (TDD).

Covers FR-01.1 (path-prefix routing), FR-01.4 (404 on unknown path),
and D-02 (14 registered prefixes), D-03 (critical flags).
"""

import pytest

from app.routing.matcher import match_route
from app.routing.registry import RouteConfig, build_route_table

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def routes() -> list[RouteConfig]:
    """Route table built from representative env-style config."""
    upstream = {
        "users": "http://user-svc:8000",
        "pets": "http://pet-svc:8000",
        "posts": "http://post-svc:8000",
        "feed": "http://post-svc:8000",
        "social": "http://social-svc:8000",
        "capture": "http://capture-svc:8000",
        "send": "http://send-svc:8000",
        "view": "http://view-svc:8000",
        "responses": "http://response-svc:8000",
        "history": "http://history-svc:8000",
        "onboarding": "http://onboarding-svc:8000",
        "notifications": "http://notification-svc:8000",
        "settings": "http://setting-svc:8000",
        "ai": "http://ai-svc:8000",
    }
    return build_route_table(upstream)


# ---------------------------------------------------------------------------
# Basic routing
# ---------------------------------------------------------------------------


class TestMatchRoute:
    def test_pets_path_matches_pet_service(self, routes):
        result = match_route("/pets/123", routes)
        assert result is not None
        assert result.route_id == "pets"

    def test_users_path_matches_user_service(self, routes):
        result = match_route("/users/me", routes)
        assert result is not None
        assert result.route_id == "users"

    def test_feed_alias_matches_post_service(self, routes):
        result = match_route("/feed/timeline", routes)
        assert result is not None
        assert result.route_id == "feed"

    def test_capture_path_matches_capture_service(self, routes):
        result = match_route("/capture/upload", routes)
        assert result is not None
        assert result.route_id == "capture"

    def test_onboarding_matches(self, routes):
        result = match_route("/onboarding/start", routes)
        assert result is not None
        assert result.route_id == "onboarding"

    def test_ai_path_matches_ai_service(self, routes):
        result = match_route("/ai/analyze", routes)
        assert result is not None
        assert result.route_id == "ai"

    def test_unknown_path_returns_none(self, routes):
        assert match_route("/unknown/path", routes) is None

    def test_root_path_returns_none(self, routes):
        assert match_route("/", routes) is None

    def test_empty_path_returns_none(self, routes):
        assert match_route("", routes) is None


# ---------------------------------------------------------------------------
# Longest prefix match
# ---------------------------------------------------------------------------


class TestLongestPrefixMatch:
    def test_responses_not_confused_with_shorter_prefix(self, routes):
        """'/responses/...' must match 'responses', not any shorter prefix."""
        result = match_route("/responses/abc", routes)
        assert result is not None
        assert result.route_id == "responses"

    def test_notifications_not_confused_with_shorter_prefix(self, routes):
        result = match_route("/notifications/push", routes)
        assert result is not None
        assert result.route_id == "notifications"

    def test_settings_distinct_from_send(self, routes):
        result = match_route("/settings/profile", routes)
        assert result is not None
        assert result.route_id == "settings"


# ---------------------------------------------------------------------------
# RouteConfig attributes
# ---------------------------------------------------------------------------


class TestRouteConfig:
    def test_capture_has_per_route_limit(self, routes):
        result = match_route("/capture/anything", routes)
        assert result is not None
        assert result.rate_limit_per_min is not None
        assert result.rate_limit_per_min > 0

    def test_non_capture_has_no_per_route_limit(self, routes):
        result = match_route("/pets/123", routes)
        assert result is not None
        assert result.rate_limit_per_min is None

    def test_ai_route_is_flagged(self, routes):
        result = match_route("/ai/analyze", routes)
        assert result is not None
        assert result.is_ai is True

    def test_non_ai_route_not_flagged(self, routes):
        result = match_route("/pets/123", routes)
        assert result is not None
        assert result.is_ai is False


# ---------------------------------------------------------------------------
# Critical flags (D-03)
# ---------------------------------------------------------------------------


class TestCriticalFlags:
    _CRITICAL = {"users", "pets", "onboarding"}
    _NON_CRITICAL = {
        "posts",
        "feed",
        "social",
        "capture",
        "send",
        "view",
        "responses",
        "history",
        "notifications",
        "settings",
        "ai",
    }

    def test_critical_routes_are_marked(self, routes):
        for route in routes:
            if route.route_id in self._CRITICAL:
                assert route.is_critical is True, (
                    f"{route.route_id} should be critical"
                )

    def test_non_critical_routes_are_not_marked(self, routes):
        for route in routes:
            if route.route_id in self._NON_CRITICAL:
                assert route.is_critical is False, (
                    f"{route.route_id} should NOT be critical"
                )


# ---------------------------------------------------------------------------
# All 14 routes registered
# ---------------------------------------------------------------------------


class TestRouteTableCompleteness:
    _EXPECTED_IDS = {
        "users",
        "pets",
        "posts",
        "feed",
        "social",
        "capture",
        "send",
        "view",
        "responses",
        "history",
        "onboarding",
        "notifications",
        "settings",
        "ai",
    }

    def test_all_14_routes_present(self, routes):
        registered = {r.route_id for r in routes}
        assert registered == self._EXPECTED_IDS

    def test_all_routes_have_upstream_url(self, routes):
        for route in routes:
            assert route.upstream_url, (
                f"route '{route.route_id}' has empty upstream_url"
            )

    def test_all_routes_have_prefix(self, routes):
        for route in routes:
            assert route.prefix.startswith("/"), (
                f"route '{route.route_id}' prefix must start with '/'"
            )
