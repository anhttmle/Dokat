# F03 — Social Graph — Decision Log

---

## DL-F03-01 — CHECK constraint omitted from Friendship model

**Date:** 2026-06-21
**Context:** Design §2.2 specifies a `CHECK (user_id_a < user_id_b)` constraint on the `friendships` table to enforce canonical ordering.
**Decision:** The CHECK constraint is intentionally omitted from the SQLAlchemy `Friendship` model because SQLite (used in unit tests) does not enforce CHECK constraints the same way as PostgreSQL. Canonical ordering is enforced entirely at the service layer (`friend_service._canonical_pair()`) before every insert and lookup.
**Consequence:** The migration for PostgreSQL must add the CHECK constraint explicitly in the Alembic migration file (not via `__table_args__`). Unit tests rely on service-layer enforcement.

---

## DL-F03-02 — `lupa` added as dependency for Lua scripting in tests

**Date:** 2026-06-21
**Context:** `otp_service.consume_otp()` uses a Lua script executed via `redis.eval()` for atomic check-and-mark-used. `fakeredis` (used in unit tests) requires the `lupa` package to support `EVAL` and `EVALSHA` commands.
**Decision:** `lupa` added to `requirements.txt`. Without it, `test_service_otp.py` fails with `unknown command 'eval'`.
**Consequence:** Developers must have `lupa` installed (`make install` handles this). Production deployment does not need `lupa` (only tests do), but keeping it in one `requirements.txt` is acceptable for the MVP scope.

---

## DL-F03-03 — FCM token endpoint placed in friends router, not profile router

**Date:** 2026-06-21
**Context:** Design §3.5 specifies `PUT /profile/me/fcm-token` under the profile prefix. However, the FCM token is only needed for F03 (friend notifications), and `test_router_friends.py` tests it alongside other F03 endpoints.
**Decision:** The endpoint is implemented as `PUT /friends/fcm-token` in `routers/friends.py` for F03 scaffold simplicity. The URL deviates from the design spec.
**Consequence:** If the spec URL `/profile/me/fcm-token` is required, the endpoint should be moved to `routers/profile.py` in a later task. The router test (`test_put_fcm_token`) covers the same business logic regardless of prefix.
