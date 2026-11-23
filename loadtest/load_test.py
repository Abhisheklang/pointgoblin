"""Load test for PointGoblin WebSocket rooms.

Usage:
    python load_test.py --clients 300 --base http://localhost:8000

Phases, all measured and printed as JSON:
1. Connect: every client opens a WebSocket to the same room.
2. Single vote broadcast: one client votes and we time how long the
   update takes to reach every other client.
3. Everyone votes: all clients vote at once and we time full convergence,
   meaning every client has seen every vote, and count messages per second.
"""

import argparse
import asyncio
import json
import statistics
import time

import httpx
import websockets


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * fraction))], 1)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", type=int, default=200)
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    ws_base = args.base.replace("http://", "ws://").replace("https://", "wss://")
    total = args.clients

    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        stamp = int(time.time())
        reg = await client.post(
            f"{args.base}/api/auth/register",
            json={
                "email": f"load{stamp}@example.com",
                "name": "Load Host",
                "password": "password123",
            },
        )
        host_token = reg.json()["access_token"]
        room = await client.post(
            f"{args.base}/api/rooms",
            json={"name": "Load test room"},
            headers={"Authorization": f"Bearer {host_token}"},
        )
        code = room.json()["room"]["code"]
        await client.post(
            f"{args.base}/api/rooms/{code}/stories",
            json={"title": "Load test story"},
            headers={"Authorization": f"Bearer {host_token}"},
        )
        guest_tokens: list[str] = []
        for index in range(total):
            joined = await client.post(
                f"{args.base}/api/rooms/join",
                json={"code": code, "name": f"Load Guest {index}"},
            )
            guest_tokens.append(joined.json()["access_token"])

    sockets: list[websockets.WebSocketClientProtocol] = []
    connect_ms: list[float] = []
    messages_received = 0
    latest_count: dict[int, int] = {}
    count_seen_at: dict[int, float] = {}

    async def connect_one(index: int, token: str) -> None:
        started = time.perf_counter()
        socket = await websockets.connect(
            f"{ws_base}/ws/rooms/{code}?token={token}", max_size=2**24
        )
        connect_ms.append((time.perf_counter() - started) * 1000)
        sockets.append(socket)

        async def reader() -> None:
            nonlocal messages_received
            try:
                async for raw in socket:
                    messages_received += 1
                    message = json.loads(raw)
                    if message.get("type") == "state" and message.get("round"):
                        count = int(message["round"]["vote_count"])
                        if count > latest_count.get(index, -1):
                            latest_count[index] = count
                            count_seen_at[count] = time.perf_counter()
            except websockets.ConnectionClosed:
                pass

        asyncio.create_task(reader())

    connect_started = time.perf_counter()
    await asyncio.gather(
        *(connect_one(i, token) for i, token in enumerate(guest_tokens)),
        return_exceptions=True,
    )
    connect_wall = time.perf_counter() - connect_started
    connected = len(sockets)

    async def wait_for_count(target: int, timeout: float) -> float | None:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            reached = sum(1 for value in latest_count.values() if value >= target)
            if reached >= connected:
                return time.perf_counter()
            await asyncio.sleep(0.05)
        return None

    await wait_for_count(0, 30)

    single_started = time.perf_counter()
    await sockets[0].send(json.dumps({"action": "vote", "value": "5"}))
    single_done = await wait_for_count(1, 60)
    single_ms = None if single_done is None else round((single_done - single_started) * 1000, 1)

    phase_started = time.perf_counter()
    messages_before = messages_received
    for socket in sockets:
        await socket.send(json.dumps({"action": "vote", "value": "8"}))
    full_done = await wait_for_count(total, 90)
    phase_seconds = (full_done or time.perf_counter()) - phase_started
    phase_messages = messages_received - messages_before

    for socket in sockets:
        await socket.close()

    report = {
        "clients_requested": total,
        "clients_connected": connected,
        "connect_wall_seconds": round(connect_wall, 2),
        "connect_ms_median": round(statistics.median(connect_ms), 1) if connect_ms else None,
        "connect_ms_p95": percentile(connect_ms, 0.95),
        "single_vote_reached_all_ms": single_ms,
        "all_votes_converged": full_done is not None,
        "convergence_seconds": round(phase_seconds, 2),
        "messages_in_convergence_phase": phase_messages,
        "messages_per_second": round(phase_messages / phase_seconds, 1)
        if phase_seconds
        else None,
        "total_messages_received": messages_received,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
