"""Room and voting business logic, plus room state assembly."""

import statistics
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import repositories
from app.errors import bad_request, forbidden, not_found
from app.events import bus
from app.models import Room, Story, User

DECK = ["0", "1", "2", "3", "5", "8", "13", "21", "?", "pass"]
NUMERIC = {value for value in DECK if value.isdigit()}


def numeric_average(values: list[str]) -> float | None:
    numbers = [int(v) for v in values if v in NUMERIC]
    if not numbers:
        return None
    return round(statistics.fmean(numbers), 1)


def agreement_percent(values: list[str]) -> int | None:
    numbers = [v for v in values if v in NUMERIC]
    if not numbers:
        return None
    top = max(set(numbers), key=numbers.count)
    return round(100 * numbers.count(top) / len(numbers))


def require_room(db: Session, code: str) -> Room:
    room = repositories.get_room_by_code(db, code)
    if room is None:
        raise not_found("That room code does not exist")
    return room


def require_host(room: Room, actor: dict[str, Any]) -> None:
    if actor.get("scope") != "user" or room.host_id != actor.get("sub"):
        raise forbidden("Only the host can do that")


def participant_key(actor: dict[str, Any]) -> str:
    return str(actor.get("sub", "unknown"))


def collect_room_data(db: Session, room: Room) -> dict[str, Any]:
    """Read everything the room state needs from the database.

    This function is pure blocking database work. Async callers run it in a
    thread so the event loop stays free for socket traffic.
    """
    stories = repositories.list_stories(db, room.id)
    active = next((s for s in stories if s.status in ("active", "revealed")), None)
    votes_data: list[dict[str, str]] = []
    if active is not None:
        votes_data = [
            {"name": v.participant_name, "value": v.value}
            for v in repositories.list_votes(db, active.id)
        ]
    return {
        "room": {
            "code": room.code,
            "name": room.name,
            "host_name": room.host.name if room.host else None,
        },
        "stories": [{"id": s.id, "title": s.title, "status": s.status} for s in stories],
        "active_id": active.id if active is not None else None,
        "active_status": active.status if active is not None else None,
        "votes": votes_data,
    }


def assemble_state(data: dict[str, Any], people: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine database data and live presence into the public room state.

    Vote values stay hidden until the round is revealed.
    """
    round_data: dict[str, Any] | None = None
    if data["active_id"] is not None:
        votes = data["votes"]
        revealed = data["active_status"] == "revealed"
        round_data = {
            "story_id": data["active_id"],
            "revealed": revealed,
            "voted": [v["name"] for v in votes],
            "vote_count": len(votes),
            "results": None,
        }
        if revealed:
            values = [v["value"] for v in votes]
            round_data["results"] = {
                "votes": sorted(votes, key=lambda item: item["name"].lower()),
                "average": numeric_average(values),
                "agreement": agreement_percent(values),
            }
    return {
        "type": "state",
        "room": data["room"],
        "deck": DECK,
        "participants": people,
        "stories": data["stories"],
        "round": round_data,
    }


async def build_state(db: Session, room: Room) -> dict[str, Any]:
    people = await bus.get_presence(room.code)
    return assemble_state(collect_room_data(db, room), people)


async def broadcast_state(db: Session, room: Room) -> dict[str, Any]:
    state = await build_state(db, room)
    await bus.publish(f"room:{room.code}", state)
    return state


def cast_vote(db: Session, room: Room, actor: dict[str, Any], value: str) -> Story:
    if value not in DECK:
        raise bad_request("Pick a card from the deck")
    story = repositories.get_active_story(db, room.id)
    if story is None:
        raise bad_request("There is no active story to vote on")
    if story.status == "revealed":
        raise bad_request("Votes are already revealed for this story")
    repositories.upsert_vote(db, story.id, participant_key(actor), str(actor["name"]), value)
    return story


def reveal_votes(db: Session, room: Room, actor: dict[str, Any]) -> Story:
    require_host(room, actor)
    story = repositories.get_active_story(db, room.id)
    if story is None:
        raise bad_request("There is no active story to reveal")
    story.status = "revealed"
    db.commit()
    return story


def reset_round(db: Session, room: Room, actor: dict[str, Any]) -> Story:
    require_host(room, actor)
    story = repositories.get_active_story(db, room.id)
    if story is None:
        raise bad_request("There is no active story to reset")
    repositories.delete_votes_for_story(db, story.id)
    story.status = "active"
    db.commit()
    return story


def add_story(db: Session, room: Room, actor: dict[str, Any], title: str) -> Story:
    require_host(room, actor)
    story = repositories.create_story(db, room.id, title)
    if repositories.get_active_story(db, room.id) is None:
        story.status = "active"
        db.commit()
    return story


def activate_story(db: Session, room: Room, actor: dict[str, Any], story_id: str) -> Story:
    require_host(room, actor)
    target = repositories.get_story(db, story_id)
    if target is None or target.room_id != room.id:
        raise not_found("That story does not exist in this room")
    for story in repositories.list_stories(db, room.id):
        if story.status in ("active", "revealed") and story.id != target.id:
            story.status = "done"
    target.status = "active"
    db.commit()
    return target


def register_user(db: Session, email: str, name: str, password_hash: str) -> User:
    if repositories.get_user_by_email(db, email) is not None:
        raise bad_request("An account with that email already exists")
    try:
        return repositories.create_user(db, email, name, password_hash)
    except IntegrityError:
        # A concurrent registration with the same email won the race between
        # the check above and the insert. The loser gets the same duplicate
        # email 400 the pre-check raises, never a 500.
        db.rollback()
        raise bad_request("An account with that email already exists") from None
