"""Regression tests for the wave 2 suspect fixes (S1 to S7 plus S6 adjacent).

The race tests are ports of the barrier-synchronised probes from the verdict
pass, with iteration counts tuned down to stay CI friendly while still
exercising the races hard enough that the old code failed them reliably.
"""

import threading

from app import models, repositories, services
from app.database import SessionLocal
from app.errors import AppError


def _run_threads(workers):
    """Run worker callables simultaneously behind a barrier. Returns errors."""
    barrier = threading.Barrier(len(workers))
    errors = []

    def wrap(fn):
        def run():
            db = SessionLocal()
            try:
                barrier.wait(timeout=15)
                fn(db)
            except Exception as exc:  # noqa: BLE001 - tests record everything
                errors.append(exc)
            finally:
                db.close()

        return run

    threads = [threading.Thread(target=wrap(fn)) for fn in workers]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return errors


def _make_room_with_story():
    db = SessionLocal()
    room = repositories.create_room(db, "Race room", None)
    story = repositories.create_story(db, room.id, "Story one")
    room_id, story_id = room.id, story.id
    db.close()
    return room_id, story_id


# ---------------------------------------------------------------- S1


def test_s1_concurrent_first_votes_converge_without_errors():
    for _ in range(30):
        _, story_id = _make_room_with_story()

        def make_worker(story_id, value):
            def work(db):
                repositories.upsert_vote(db, story_id, "participant-1", "Pat", value)  # noqa: B023

            return work

        errors = _run_threads([make_worker(story_id, "5"), make_worker(story_id, "8")])
        assert errors == []
        db = SessionLocal()
        votes = repositories.list_votes(db, story_id)
        db.close()
        assert len(votes) == 1
        assert votes[0].value in ("5", "8")


def test_s1_eight_thread_vote_race_loses_no_vote():
    for _ in range(20):
        _, story_id = _make_room_with_story()

        def make_worker(story_id, value):
            def work(db):
                repositories.upsert_vote(db, story_id, "participant-1", "Pat", value)  # noqa: B023

            return work

        errors = _run_threads([make_worker(story_id, str(n)) for n in range(8)])
        assert errors == []
        db = SessionLocal()
        votes = repositories.list_votes(db, story_id)
        db.close()
        assert len(votes) == 1


# ---------------------------------------------------------------- S2


def test_s2_duplicate_email_registration_race_loser_gets_400():
    for i in range(50):
        email = f"racer{i}@example.com"

        def make_worker(email):
            def work(db):
                services.register_user(db, email, "Racer", "not-a-real-hash")  # noqa: B023

            return work

        errors = _run_threads([make_worker(email), make_worker(email)])
        # Exactly one thread wins; the loser must see the duplicate-email
        # AppError (400), never an IntegrityError escaping as a 500.
        assert len(errors) == 1
        assert isinstance(errors[0], AppError)
        assert errors[0].status_code == 400
        db = SessionLocal()
        count = db.query(models.User).filter_by(email=email).count()
        db.close()
        assert count == 1


# ---------------------------------------------------------------- S3


def test_s3_concurrent_create_story_positions_stay_unique():
    for _ in range(50):
        db = SessionLocal()
        room = repositories.create_room(db, "Pos room", None)
        room_id = room.id
        db.close()

        def make_worker(room_id, title):
            def work(db):
                repositories.create_story(db, room_id, title)  # noqa: B023

            return work

        errors = _run_threads([make_worker(room_id, f"t{n}") for n in range(4)])
        assert errors == []
        db = SessionLocal()
        positions = sorted(s.position for s in repositories.list_stories(db, room_id))
        db.close()
        assert positions == [0, 1, 2, 3]


def test_s3_concurrent_add_story_never_two_active():
    for i in range(100):
        db = SessionLocal()
        user = repositories.create_user(db, f"hostrace{i}@example.com", "Host", "hash")
        room = repositories.create_room(db, "Add race", user.id)
        code, host_id = room.code, user.id
        db.close()
        actor = {"sub": host_id, "scope": "user", "name": "Host"}

        def make_worker(code, actor, title):
            def work(db):
                rm = repositories.get_room_by_code(db, code)  # noqa: B023
                services.add_story(db, rm, actor, title)  # noqa: B023

            return work

        errors = _run_threads([make_worker(code, actor, "Alpha"), make_worker(code, actor, "Beta")])
        assert errors == []
        db = SessionLocal()
        rm = repositories.get_room_by_code(db, code)
        actives = [
            s for s in repositories.list_stories(db, rm.id) if s.status in ("active", "revealed")
        ]
        db.close()
        assert len(actives) <= 1


def test_s3_selectors_agree_on_constructed_two_active_state():
    """Legacy two-active state built directly: both selectors must agree."""
    db = SessionLocal()
    room = repositories.create_room(db, "Mismatch room", None)
    first = repositories.create_story(db, room.id, "First story")
    second = repositories.create_story(db, room.id, "Second story")
    first.status = "active"
    second.status = "active"
    db.commit()
    data = services.collect_room_data(db, room)
    active = repositories.get_active_story(db, room.id)
    db.close()
    assert active is not None
    assert data["active_id"] == active.id


def test_s3_activate_story_still_deactivates_others_sequentially():
    db = SessionLocal()
    user = repositories.create_user(db, "host3@example.com", "Host", "hash")
    room = repositories.create_room(db, "Activate room", user.id)
    actor = {"sub": user.id, "scope": "user", "name": "Host"}
    s1 = services.add_story(db, room, actor, "One")
    s2 = services.add_story(db, room, actor, "Two")
    services.activate_story(db, room, actor, s2.id)
    db.expire_all()
    statuses = {s.title: s.status for s in repositories.list_stories(db, room.id)}
    assert statuses == {"One": "done", "Two": "active"}
    services.reveal_votes(db, room, actor)
    services.activate_story(db, room, actor, s1.id)
    db.expire_all()
    statuses_after = {s.title: s.status for s in repositories.list_stories(db, room.id)}
    db.close()
    assert statuses_after == {"One": "active", "Two": "done"}


# ---------------------------------------------------------------- S4


def test_s4_subscription_queue_is_bounded_and_drops_oldest():
    import asyncio

    from app.config import get_settings
    from app.events import MemoryBus

    async def run():
        bus = MemoryBus()
        sub = await bus.subscribe("room:ABC123")
        cap = get_settings().subscription_queue_maxsize
        assert sub.queue.maxsize == cap
        for n in range(1000):
            await bus.publish("room:ABC123", {"type": "state", "n": n})
        assert sub.queue.qsize() == cap
        assert sub.dropped == 1000 - cap
        # Drop-oldest: the surviving messages are the most recent ones.
        import json

        last = None
        while not sub.queue.empty():
            last = json.loads(sub.queue.get_nowait())
        assert last == {"type": "state", "n": 999}

    asyncio.run(run())


# ---------------------------------------------------------------- S5


class _FakeRedis:
    """Minimal async Redis stand-in honoring per-key expiry deadlines."""

    def __init__(self):
        self.store = {}
        self.deadlines = {}

    async def set(self, key, value, ex=None):
        import time as _time

        self.store[key] = value
        self.deadlines[key] = None if ex is None else _time.monotonic() + ex

    async def get(self, key):
        import time as _time

        deadline = self.deadlines.get(key)
        if deadline is not None and deadline <= _time.monotonic():
            return None
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)
        self.deadlines.pop(key, None)

    async def scan_iter(self, match=None):
        import fnmatch

        for key in list(self.store):
            if match is None or fnmatch.fnmatch(key, match):
                yield key


def test_s5_redis_presence_is_per_participant_with_own_ttl():
    import asyncio

    from app.config import get_settings
    from app.events import RedisBus

    async def run():
        bus = RedisBus("redis://localhost:6399/0")
        fake = _FakeRedis()
        bus._redis = fake
        ttl = get_settings().presence_ttl_seconds
        assert ttl <= 600  # minutes, not the old 12 hours

        await bus.set_presence("GHOST1", "user-123", "Ghost User", False)
        ghost_key = "presence:GHOST1:user-123"
        assert ghost_key in fake.store
        ghost_deadline = fake.deadlines[ghost_key]
        assert ghost_deadline is not None

        # A second participant joining must not touch the ghost's deadline.
        await bus.set_presence("GHOST1", "user-999", "Second Joiner", True)
        assert fake.deadlines[ghost_key] == ghost_deadline

        people = await bus.get_presence("GHOST1")
        assert {p["name"] for p in people} == {"Ghost User", "Second Joiner"}

        # Simulate the crash plus TTL passing for the ghost only.
        fake.deadlines[ghost_key] = 0
        people = await bus.get_presence("GHOST1")
        assert [p["name"] for p in people] == ["Second Joiner"]

        await bus.remove_presence("GHOST1", "user-999")
        assert await bus.get_presence("GHOST1") == []

    asyncio.run(run())


def test_s5_memory_bus_presence_expires_per_participant(monkeypatch):
    import asyncio

    from app.config import get_settings
    from app.events import MemoryBus

    monkeypatch.setattr(get_settings(), "presence_ttl_seconds", 0)

    async def run():
        bus = MemoryBus()
        await bus.set_presence("ROOM1", "user-1", "Ghost", False)
        # TTL of 0 means the entry is already expired on the next read.
        assert await bus.get_presence("ROOM1") == []

    asyncio.run(run())


# ---------------------------------------------------------------- S7


def test_s7_unknown_email_login_still_pays_bcrypt_cost(client, monkeypatch):
    from app.routes import auth as auth_route
    from app.security import DUMMY_PASSWORD_HASH
    from tests.conftest import register_host

    register_host(client, email="timing@example.com")
    seen_hashes = []
    real_verify = auth_route.verify_password

    def spy(password, password_hash):
        seen_hashes.append(password_hash)
        return real_verify(password, password_hash)

    monkeypatch.setattr(auth_route, "verify_password", spy)
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody-here@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401
    # The unknown-email path verified against the dummy bcrypt hash.
    assert seen_hashes == [DUMMY_PASSWORD_HASH]

    seen_hashes.clear()
    response = client.post(
        "/api/auth/login",
        json={"email": "timing@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert len(seen_hashes) == 1
    assert seen_hashes[0] != DUMMY_PASSWORD_HASH
