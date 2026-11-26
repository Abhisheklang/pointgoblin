"""Data access functions. Routes and services never write queries directly."""

import secrets
import string

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import models

CODE_ALPHABET = string.ascii_uppercase + string.digits


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email.lower()).first()


def create_user(db: Session, email: str, name: str, password_hash: str) -> models.User:
    user = models.User(email=email.lower(), name=name, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_room_by_code(db: Session, code: str) -> models.Room | None:
    return db.query(models.Room).filter(models.Room.code == code.upper()).first()


def generate_room_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if get_room_by_code(db, code) is None:
            return code


def create_room(db: Session, name: str, host_id: str | None) -> models.Room:
    room = models.Room(code=generate_room_code(db), name=name, host_id=host_id)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def list_stories(db: Session, room_id: str) -> list[models.Story]:
    return (
        db.query(models.Story)
        .filter(models.Story.room_id == room_id)
        .order_by(models.Story.position)
        .all()
    )


def get_story(db: Session, story_id: str) -> models.Story | None:
    return db.query(models.Story).filter(models.Story.id == story_id).first()


def get_active_story(db: Session, room_id: str) -> models.Story | None:
    return (
        db.query(models.Story)
        .filter(models.Story.room_id == room_id, models.Story.status.in_(["active", "revealed"]))
        .order_by(models.Story.position.desc())
        .first()
    )


def lock_room(db: Session, room_id: str) -> models.Room | None:
    """Lock the room row for the rest of the transaction.

    Serializes guarded room writes (story activation) on databases with row
    locks. On SQLite this is a plain read; the write lock still serializes
    the transaction itself.
    """
    return db.query(models.Room).filter(models.Room.id == room_id).with_for_update().first()


def create_story(db: Session, room_id: str, title: str) -> models.Story:
    # Position is max(position) + 1, retried against the unique constraint on
    # (room_id, position): a concurrent creator that commits first makes our
    # position stale, the constraint rejects the insert, and we recompute
    # instead of landing a duplicate position.
    last_error: Exception | None = None
    for _ in range(20):
        max_position = (
            db.query(func.max(models.Story.position))
            .filter(models.Story.room_id == room_id)
            .scalar()
        )
        position = 0 if max_position is None else max_position + 1
        story = models.Story(room_id=room_id, title=title, position=position)
        db.add(story)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
            continue
        except OperationalError as exc:
            db.rollback()
            if "locked" not in str(exc).lower():
                raise
            last_error = exc
            continue
        db.refresh(story)
        return story
    assert last_error is not None
    raise last_error


def list_votes(db: Session, story_id: str) -> list[models.Vote]:
    return db.query(models.Vote).filter(models.Vote.story_id == story_id).all()


def _find_vote(db: Session, story_id: str, participant_key: str) -> models.Vote | None:
    return (
        db.query(models.Vote)
        .filter(
            models.Vote.story_id == story_id,
            models.Vote.participant_key == participant_key,
        )
        .first()
    )


def upsert_vote(
    db: Session, story_id: str, participant_key: str, participant_name: str, value: str
) -> models.Vote:
    vote = _find_vote(db, story_id, participant_key)
    if vote is not None:
        vote.value = value
        vote.participant_name = participant_name
        db.commit()
        db.refresh(vote)
        return vote
    vote = models.Vote(
        story_id=story_id,
        participant_key=participant_key,
        participant_name=participant_name,
        value=value,
    )
    db.add(vote)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent first vote from the same participant won the insert
        # race and hit the unique constraint on our side. Roll back and fall
        # back to updating the row the winner created, so the vote still
        # lands instead of escaping as a 500 or a silently lost vote.
        db.rollback()
        vote = _find_vote(db, story_id, participant_key)
        if vote is None:
            raise
        vote.value = value
        vote.participant_name = participant_name
        db.commit()
    db.refresh(vote)
    return vote


def delete_votes_for_story(db: Session, story_id: str) -> None:
    db.query(models.Vote).filter(models.Vote.story_id == story_id).delete()
    db.commit()
