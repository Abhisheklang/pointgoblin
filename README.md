# PointGoblin: Real Time Planning Poker, a Backend Portfolio Project

PointGoblin is a real time planning poker application built as a backend portfolio project. It demonstrates a production style stack: FastAPI, WebSockets, Redis pub sub across two API instances, PostgreSQL, JWT auth, Docker and a React front end, load tested with 300 concurrent clients in one room. A host opens a room, teammates join as guests with a short code, everyone votes in secret, and the host reveals all cards at the same moment. The result shows every vote, the average, and how much the team agrees.

![Planning poker results with average and agreement](screenshots/planning-poker-results-average-and-agreement-desktop.png)

## Background, and what this project demonstrates

Planning poker is an estimation technique built on one rule: nobody sees a vote until everybody has voted. The rule exists because of anchoring. The first number spoken in a call pulls every later number toward it, so the group ends up measuring confidence instead of the work. PointGoblin implements that rule in the protocol itself: before the reveal, room state carries voter names and a count, never values.

This repository is a backend portfolio project. It exists to demonstrate, with running code and measured numbers:

* A real time WebSocket API in FastAPI, with REST for accounts, rooms, and stories.
* State shared across two API instances through Redis publish and subscribe, proven by a cross instance check.
* Server side enforcement of hidden votes, reveal maths, and agreement scoring.
* Authentication split by role: JWT accounts for hosts, scoped guest tokens for one room.
* Load behaviour measured, not asserted: 300 concurrent clients in one room, with connection, broadcast, and convergence timings in the load test section below.

## What was built

* Host accounts with registration and sign in, protected by hashed passwords and JSON Web Tokens.
* Guest access with a scoped token that works for one room only.
* A story queue where the host adds stories and chooses which one is live.
* The classic planning poker deck: 0, 1, 2, 3, 5, 8, 13, 21, a question mark, and a pass card.
* Hidden voting with a live count of who has voted, without showing any values.
* Host reveal and reset, with results saved to PostgreSQL at reveal time.
* Live presence that shows who is in the room and who is still thinking.
* Rate limiting on sign in and room creation.
* A responsive interface that works on a phone, a tablet, and a large monitor, with motion that respects reduced motion settings.

## How a demo session runs

1. The host creates an account and opens a room.
2. The host shares the six character room code with the team.
3. Guests enter their name and the code, then land inside the room.
4. The host adds a story. Voting opens at once.
5. Everyone picks a card. The room shows who has voted and hides what they picked.
6. The host reveals. Every card flips, and the average and agreement appear.
7. The team talks, resets if needed, and moves to the next story.

## Screenshots and demo recording

[![Screen recording of a live PointGoblin session](screenshots/planning-poker-room-voting-in-progress-desktop.png)](recordings/pointgoblin-planning-poker-live-demo-720p.mp4)

The image above links to a screen recording of a real host and guest session, from opening the room to the reveal. The recording runs 45.8 seconds. The linked file is the 720p copy, and a 1080p master sits in the same recordings folder.

![Landing page on a desktop](screenshots/planning-poker-online-landing-page-desktop.png)

![Room voting in progress, host view](screenshots/planning-poker-room-voting-in-progress-desktop.png)

![Votes hidden before the reveal, guest view](screenshots/planning-poker-room-votes-hidden-before-reveal.png)

![Results with average and agreement](screenshots/planning-poker-results-average-and-agreement-desktop.png)

![Voting deck on a phone](screenshots/planning-poker-room-voting-deck-mobile.png)

![Landing page on a phone](screenshots/planning-poker-online-landing-page-mobile.png)

## Architecture

PointGoblin is split into a Python backend and a TypeScript frontend, with infrastructure that is designed to scale past one process.

* **API**: Python with FastAPI. REST routes handle accounts, rooms, stories, and votes. A WebSocket endpoint streams room state.
* **Layers**: Routes call services, services call repositories, and repositories own the database queries. Schemas validate every request and response.
* **Event bus**: Redis carries room events between API processes with publish and subscribe. One shared subscription connection per process fans messages out to local clients, and broadcasts are coalesced over a short window so join bursts do not flood the room.
* **Database**: PostgreSQL through SQLAlchemy stores users, rooms, stories, and votes. WebSocket handlers use short lived sessions, so a connected client never holds a database connection hostage.
* **Presence**: The list of people in a room lives in Redis with an expiry, separate from the permanent record.
* **Frontend**: React with TypeScript and Vite, styled with a small design system of colour, type, spacing, and motion tokens.
* **Delivery**: Docker Compose runs PostgreSQL, Redis, two API replicas, the frontend, and an nginx load balancer in front of all of it.

## Run it locally

### With Docker Compose

You need Docker with the Compose plugin.

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8080 in a browser. The landing page loads first, and the app opens from there.

### Without Docker

You need Python 3.11 or newer, Node 22, PostgreSQL, and Redis.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/pointgoblin \
REDIS_URL=redis://localhost:6379/0 EVENT_BUS=redis JWT_SECRET=local-dev-secret \
.venv/bin/uvicorn app.main:app --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in a browser.

If Redis is not running, set EVENT_BUS to memory. The app then works inside one process, which is handy for a quick trial and for the test suite.

## Tests

The backend test suite covers accounts, room flow, voting rules, reveal maths, permissions, and a live WebSocket session where two clients share one room.

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
.venv/bin/ruff check app tests
.venv/bin/black --check app tests
```

The frontend checks run with:

```bash
cd frontend
npm run lint
npm run format:check
npm run build
```

## Load test results

The load test script connects many WebSocket clients to one room, measures connection time, then times a single vote travelling to every client, then has every client vote at once and times full convergence.

```bash
cd backend
.venv/bin/python ../loadtest/load_test.py --clients 300 --base http://localhost:8000
```

Measured on the development virtual machine used for this build (a small shared box, one API process, local PostgreSQL and Redis):

* 300 of 300 clients connected. Median connect time 474 ms, 95th percentile 1440 ms.
* One vote reached all 300 clients in 192 ms.
* All 300 clients voting at once converged in 2.23 seconds, with 5,151 state messages delivered in total and zero server errors.

A second script, `loadtest/cross_instance_check.py`, proves the scaling story: a guest connected to one API instance votes, and a host connected to a second instance receives the update through Redis.

## Known limits

* The Docker Compose file is written and validated, but Docker was not available in the build environment, so Compose itself was never run there. Every service in it was run and verified directly instead.
* The display fonts load from a public font service at runtime. Fallbacks are declared, and the layout holds without them.
* Screenshots and the recording were captured in a local trial configuration (SQLite with the in memory event bus). The PostgreSQL and Redis path was verified separately with two API instances.
* There is no public deployment. All numbers in this README come from the local machine described in the load test section.

## Animation

Motion in PointGoblin explains a change of state, nothing more. Durations and easing live in one place in the theme: 120 ms for small feedback, 200 ms for entrances, and 450 ms for the card reveal, which is the signature moment of the application. Animations use transforms and opacity only. When a person asks their system for reduced motion, the app honours it and the animations switch off.

## Technical notes

### What is planning poker?

Planning poker is an estimation technique from agile software development. The team discusses a story, each person secretly picks a card with a story point value, and all cards are revealed together. The team then agrees on one estimate.

### Why do votes stay hidden?

Hidden votes stop anchoring. When the first estimate is spoken out loud, later estimates drift toward it, and the team ends up measuring confidence instead of the work. Revealing every card at once keeps each judgement independent.

### What does the agreement number mean?

Agreement is the share of numeric votes that match the most common value. High agreement means the team already sees the story the same way. Low agreement is useful too, because it points at the misunderstanding the team should talk about.

### Can guests vote without an account?

Yes. Only the host needs an account. Guests join with the room code and a display name, and their token works for that room only.

## Interview defence: design choices and limits

This section explains the choices a reviewer is most likely to challenge.

**Why Redis publish and subscribe for room events?**
Because a single process cannot be the ceiling. With events in Redis, any API instance can serve any client, and a vote handled by one instance reaches clients held by another. The cross instance check in the loadtest folder proves this against two live processes, not just in theory.

**Why does each process keep one shared subscription connection?**
An early version opened one Redis connection per client subscription. At a few hundred clients the connection pool ran dry and messages stopped. One shared connection per process, with channels multiplexed over it and a self healing listener, removed the ceiling and cut the connection count to a handful.

**Why coalesce broadcasts?**
The first load test delivered 221,413 messages for 300 clients, because every join triggered a full state broadcast to everyone. Coalescing triggers inside a 75 ms window into one broadcast of the latest state cut that to about five thousand messages and dropped the single vote travel time from about 21 seconds to about 0.2 seconds. The lesson is that correctness at ten clients can still be a flood at three hundred.

**Why short lived database sessions in the WebSocket handler?**
The first version held one session for the life of each socket, which pinned one pooled connection per client and exhausted the pool. Sessions now open for one unit of work and close, and blocking database reads run in a worker thread so the event loop stays free for socket traffic.

**What breaks first at ten thousand clients?**
Three things, in this order. First, one room with ten thousand people in it would still fan every state change out to ten thousand sockets from one channel, so very large rooms need sharded fanout or a dedicated realtime tier. Second, presence in one Redis hash per room grows linearly and should move to a structure with paging. Third, a single PostgreSQL writer handles the vote writes comfortably at this scale, but reveal time result writes across many busy rooms would justify a queue. None of these matter for a planning session, which is a small group by design, and naming them honestly matters more than pretending the design is infinite.

**Why are vote values hidden in the API as well as the screen?**
Because hiding values only in the interface is theatre. Before reveal, the room state contains voter names and a count, never values, so no client can peek by reading network traffic.

## Project layout

```text
backend/    FastAPI app with routes, services, repositories, and tests
frontend/   React app plus the static landing page
loadtest/   WebSocket load test and the cross instance check
nginx/      Load balancer configuration for Compose
screenshots/  Screenshots used in this README
recordings/   A screen recording of a full live session
```

## Credits and licence

Developed by [Abhisheklang](https://github.com/Abhisheklang).

Released under the MIT licence. See the LICENSE file.
