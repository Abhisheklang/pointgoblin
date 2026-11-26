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
