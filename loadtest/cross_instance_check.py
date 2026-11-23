"""Cross instance proof.

A host connects to API instance one and a guest connects to API instance
two. The guest votes on instance two. The host must receive the updated
state on instance one, which only works if events travel through Redis.
"""

import asyncio
import json
import sys

import httpx
import websockets

API_ONE = "http://localhost:8000"
API_TWO = "http://localhost:8001"
WS_ONE = "ws://localhost:8000"
WS_TWO = "ws://localhost:8001"


async def main() -> int:
    async with httpx.AsyncClient(trust_env=False) as client:
        reg = await client.post(
            f"{API_ONE}/api/auth/register",
            json={
                "email": "cross@example.com",
                "name": "Cross Host",
                "password": "password123",
            },
        )
        if reg.status_code == 400:
            reg = await client.post(
                f"{API_ONE}/api/auth/login",
                json={"email": "cross@example.com", "password": "password123"},
            )
        host_token = reg.json()["access_token"]
        room = await client.post(
            f"{API_ONE}/api/rooms",
            json={"name": "Cross instance room"},
            headers={"Authorization": f"Bearer {host_token}"},
        )
        code = room.json()["room"]["code"]
        await client.post(
            f"{API_ONE}/api/rooms/{code}/stories",
            json={"title": "Cross instance story"},
            headers={"Authorization": f"Bearer {host_token}"},
        )
        guest = await client.post(
            f"{API_TWO}/api/rooms/join", json={"code": code, "name": "Cross Guest"}
        )
        guest_token = guest.json()["access_token"]

    async with websockets.connect(
        f"{WS_ONE}/ws/rooms/{code}?token={host_token}"
    ) as host_socket, websockets.connect(
        f"{WS_TWO}/ws/rooms/{code}?token={guest_token}"
    ) as guest_socket:
        await guest_socket.send(json.dumps({"action": "vote", "value": "8"}))
        deadline = asyncio.get_running_loop().time() + 10
        while asyncio.get_running_loop().time() < deadline:
            message = json.loads(await asyncio.wait_for(host_socket.recv(), timeout=10))
            if (
                message.get("type") == "state"
                and message.get("round")
                and message["round"]["vote_count"] >= 1
            ):
                print(
                    "PASS guest vote on instance two reached host on instance one. "
                    f"vote_count={message['round']['vote_count']} room={code}"
                )
                return 0
    print("FAIL no cross instance broadcast received")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
