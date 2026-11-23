"""Data access functions. Routes and services never write queries directly."""

import secrets
import string

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


def create_story(db: Session, room_id: str, title: str) -> models.Story:
    position = db.query(models.Story).filter(models.Story.room_id == room_id).count()
    story = models.Story(room_id=room_id, title=title, position=position)
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def list_votes(db: Session, story_id: str) -> list[models.Vote]:
    return db.query(models.Vote).filter(models.Vote.story_id == story_id).all()


def upsert_vote(
    db: Session, story_id: str, participant_key: str, participant_name: str, value: str
) -> models.Vote:
    vote = (
        db.query(models.Vote)
        .filter(
            models.Vote.story_id == story_id,
            models.Vote.participant_key == participant_key,
        )
        .first()
    )
    if vote is None:
        vote = models.Vote(
            story_id=story_id,
            participant_key=participant_key,
            participant_name=participant_name,
            value=value,
        )
        db.add(vote)
    else:
        vote.value = value
        vote.participant_name = participant_name
    db.commit()
    db.refresh(vote)
    return vote


def delete_votes_for_story(db: Session, story_id: str) -> None:
    db.query(models.Vote).filter(models.Vote.story_id == story_id).delete()
    db.commit()
