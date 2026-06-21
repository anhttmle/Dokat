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

## DL-F03-04 — Router updated as direct consequence of tasks 3.1 and 3.2

**Date:** 2026-06-21
**Context:** Task 3.1 requires `get_redis_client()` to return `redis.asyncio.Redis`. Task 3.2 requires `OTPService` async class replacing the old sync `generate_otp`/`consume_otp` functions. The existing `app/routers/friends.py` called those sync functions directly. Leaving the router unchanged would result in broken code (sync calls on an async Redis client).
**Decision:** Updated `app/routers/friends.py` as a minimal collateral change: replaced `generate_otp`/`consume_otp` calls with `OTPService` async calls, and marked the relevant endpoint handlers `async def`. Also updated mock targets in `test_router_friends.py` from the old functions to `OTPService`.
**Consequence:** The router now uses the correct async API. Task 4 (router test suite) can proceed without needing to re-migrate. This change is a direct, unavoidable consequence of tasks 3.1 and 3.2 and does not implement any new router business logic.

---

## DL-F03-05 — `list_friends()` renamed key from `friend_id` to `user_id` and added profile JOIN

**Date:** 2026-06-21
**Context:** Task 6.1 requires `list_friends()` to JOIN with the `users` table and return `display_name`, `avatar_url` alongside the friend's UUID. The original implementation returned only `friend_id` and `friendship_created_at`.
**Decision:** Renamed the key `friend_id` → `user_id` in the return dict to match Design §3.3 response format. Added a per-row `db.query(User)` lookup (N+1) rather than a SQL JOIN, to keep the implementation simple for MVP scope (max 20 friends per user, so at most 20 extra queries per request).
**Consequence:** The router's `GET /friends` handler was updated to use `f["user_id"]` directly (removing the manual `friend_id → user_id` mapping). If performance becomes a concern at scale, replace the N+1 with a single JOIN query.


**Date:** 2026-06-21
**Context:** Design §3.5 specifies `PUT /profile/me/fcm-token` under the profile prefix. However, the FCM token is only needed for F03 (friend notifications), and `test_router_friends.py` tests it alongside other F03 endpoints.
**Decision:** The endpoint is implemented as `PUT /friends/fcm-token` in `routers/friends.py` for F03 scaffold simplicity. The URL deviates from the design spec.
**Consequence:** If the spec URL `/profile/me/fcm-token` is required, the endpoint should be moved to `routers/profile.py` in a later task. The router test (`test_put_fcm_token`) covers the same business logic regardless of prefix.
