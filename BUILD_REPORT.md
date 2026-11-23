# PointGoblin Build Report

Date: 24 November 2026. Status: complete local package, verified on the development virtual machine. Nothing was published, registered, or deployed to a public host.

## What was built

PointGoblin is a live planning poker app for remote teams, built as a portfolio proof for full stack and backend job listings.

* Backend in Python with FastAPI: REST routes for accounts, rooms, stories, and votes, plus a WebSocket endpoint that streams room state.
* Layered code: routes call services, services call repositories, repositories own the queries. Pydantic schemas validate input and output.
* Redis publish and subscribe carries room events between API processes. Presence lives in Redis with an expiry.
* PostgreSQL through SQLAlchemy stores users, rooms, stories, and votes. Passwords are hashed with bcrypt. Hosts sign in with JSON Web Tokens. Guests receive a scoped token for one room.
* Rate limiting guards sign in and room creation.
* Frontend in React with strict TypeScript: a static search friendly landing page, a create and join screen, and the room with presence, a story queue, the voting deck, and results.
* Docker Compose file with PostgreSQL, Redis, two API replicas, the frontend, and an nginx load balancer. A CI workflow runs backend tests and lint plus the frontend lint and build.

## Logo

Concept in one sentence: three voting cards converge into a single point, and the front card lifts its top corner into a goblin ear.

What each element carries:

* The front card stands face down, which carries fairness. Nobody sees a vote before the reveal.
* Three cards becoming one point carries team consensus, and the point shape itself carries speed.
* The lifted corner shaped as an ear carries playful mischief. It is the only joke in the mark, kept small on purpose.
* Plain geometry, flat colour, and a strict grid carry professional trust. The mark stays readable at 16 pixels.

Delivered set: the colour mark, a lockup with the wordmark, a light background lockup, a one colour version, and favicons rendered from the vector source at 16, 32, 48, 180, 192, and 512 pixels. Files live in frontend/src/assets and frontend/public. The logo sheet screenshot shows the set on dark and light backgrounds, and the mark appears in the landing header and the room header in every screenshot and in the recording. Per the user instruction, no separate brand document was created. This section is the logo record.

Palette: goblin green #8BD450, deep moss #4C7A3F, forest ink #0B120C, cream #EAF6E3.

## Rule gates, all checked before delivery

1. **Brand domain name**: searched the whole tree for the project name followed by any common top level domain suffix. Result: 0 hits. Code and docs use localhost and relative addresses only.
2. **Trademarks**: searched user facing copy and docs for third party product and company names. Result: no product or company names in copy. The only matches in the tree are standard technical identifiers in markup, the social card meta property names and the touch icon link relation, which are protocol names rather than copy.
3. **Dash characters**: searched the whole tree for the em dash character and the en dash character. Result: 0 hits for both. Prose in the README, this report, the landing page, and the app was written without dash punctuation. Sentences use commas, colons, periods, or brackets. Hyphens remain only where they are syntax, filenames, or identifiers.
4. **Leftovers**: searched for TODO and FIXME markers, console logging in the frontend, and placeholder filler text. Result: 0 hits for each.

## Professional bar checks

* Python passes Ruff and Black with zero findings. The frontend passes ESLint and Prettier checks with zero findings, and TypeScript compiles under strict mode.
* Structured error responses everywhere, with a stable error code and a human message. Input is validated by schemas. Secrets come from environment variables, and an example env file documents every setting.
* The design system defines colour tokens, a type scale, spacing through utility classes, motion tokens, and component states for hover, focus, disabled, loading, empty, and error.
* Repository hygiene: a sensible folder layout, a gitignore, small logical commits, and a CI workflow.

## Tests

Backend suite, run with pytest against SQLite and the in memory bus: **26 passed, 0 failed.**

Coverage by file:

* test_auth.py: registration, duplicate email refusal, short password refusal, sign in success and failure, hashed password storage, room creation permissions. 8 tests.
* test_rooms.py: guest join, unknown room refusal, story creation, guest permission refusal, story activation, token requirements, unique room codes. 7 tests.
* test_voting.py: hidden values before reveal, reveal maths for average and agreement, guest reveal refusal, invalid card refusal, voting with no active story, reset behaviour, vote changes, and non numeric cards in the average. 8 tests.
* test_websocket.py: two clients in one room where a guest vote reaches the host live and a host reveal reaches the guest, bad token refusal, and guest reveal refusal over the socket. 3 tests.

Frontend: ESLint clean, Prettier clean, production build succeeds.

## Live verification on real services

Docker is not installed in this virtual machine, so the stack was verified with direct processes instead: PostgreSQL 16 and Redis 7 running locally, two API instances on ports 8000 and 8001, and the frontend dev server proxying to them.

* Health checks passed on both API instances.
* Cross instance proof, run three times with the final code: a guest connected to instance two voted, and a host connected to instance one received the update through Redis. Result: PASS each time, most recently for room PTH4HD.
* The full product flow was driven in a real browser twice, once for screenshots and once for the recording: account creation, room creation, guest join by code, story added, both votes cast with values hidden, host reveal, results shown.

## Load test, measured

Script: loadtest/load_test.py against one API instance with local PostgreSQL and Redis, 300 clients in one room.

* Clients connected: 300 of 300. Wall time to connect all: 1.67 seconds.
* Connect latency: median 474 ms, 95th percentile 1440 ms.
* One vote reached all 300 clients in 192 ms.
* All 300 clients voting at once converged in 2.23 seconds.
* Messages delivered in total: 5,151. Server errors during the run: 0. The server stayed healthy after the run, and the cross instance proof passed again immediately afterwards.

## Bugs the verification caught and fixed

Honest list, because finding these is the point of testing at scale:

1. WebSocket handlers held one database session per client for the life of the socket. The pool ran dry near 300 clients. Fixed with short lived sessions per unit of work, blocking reads moved to a worker thread, and a larger pool.
2. One Redis connection per client subscription exhausted the connection pool. Fixed with one shared subscription connection per process and channel multiplexing, plus a self healing listener that resubscribes after a failure.
3. The listener loop spun at full CPU when no channel was subscribed. Fixed by waiting while idle.
4. Every join broadcast the full room state to everyone, which delivered 221,413 messages for 300 clients. Fixed by coalescing broadcasts inside a 75 ms window, with a dirty flag so a change during a pending broadcast is never lost. The same load then delivered 5,151 messages, and one vote travel time fell from about 21 seconds to 192 ms.
5. The room layout grid had no base column definition, which caused 63 px of horizontal overflow at 360 px width. Fixed, and the responsive suite was rerun in full.

## Responsive acceptance results

Method: a real browser checked scrollWidth against clientWidth on each screen at each width, after the animation system was in place. Zero overflow is a pass.

| Screen | 360 px | 768 px | 1280 px | 1920 px |
| --- | --- | --- | --- | --- |
| Landing page | Pass | Pass | Pass | Pass |
| Create and join | Pass | Pass | Pass | Pass |
| Room with deck and results | Pass | Pass | Pass | Pass |

At 360 px the voting deck shows all ten cards inside the viewport, each at a usable touch size. Touch targets across the app are at least 40 px in the small dimension.

## Animation

One motion system, defined once in the theme. Durations: 120 ms for small feedback, 200 ms for entrances, 450 ms at most for the reveal. One easing family. Only transforms and opacity animate. The system covers the card flip on reveal, card selection feedback, people joining and leaving, page and section entrances, story queue changes, results appearing, hover states, and loading skeletons. A reduced motion preference switches the animations off. The recording shows the reveal animation in the real flow.

## Screenshots

All in the screenshots folder, all captured from the real running app:

* planning-poker-online-landing-page-desktop.png
* planning-poker-online-landing-page-mobile.png
* planning-poker-room-voting-in-progress-desktop.png
* planning-poker-room-votes-hidden-before-reveal.png
* planning-poker-results-average-and-agreement-desktop.png
* planning-poker-room-voting-deck-mobile.png
* pointgoblin-logo-set-on-dark-and-light-backgrounds.png

## Recordings

All in the recordings folder. One continuous take of a real session with two browser windows side by side: landing page, host creates the room, a guest joins with the code, the host adds a story, both vote with cards hidden, the host reveals, results show. The logo is visible in both headers throughout.

* pointgoblin-planning-poker-live-demo-1080p.mp4: 1920 by 1080, 63.3 seconds.
* pointgoblin-planning-poker-live-demo-720p.mp4: 1280 by 720, 63.3 seconds, the light copy of the same take.

Frames from the master were inspected at 5, 25, 45, and 60 seconds to confirm the flow reads correctly.

## What was not verified, plainly

* Docker Compose was not run. Docker is not installed in this virtual machine and could not be added. The Compose file and the nginx configuration were written carefully and validated as YAML and by inspection, and every service in them was verified directly with local processes instead. The one command startup is documented but unproven in this environment.
* No public deployment exists. Live hosting needs an account and a payment method, which are the owner steps. Nothing was deployed.
* Nothing was published to GitHub. No repository was created and nothing was pushed, by instruction.
* The domain was not registered. Registration is an owner step, and the codebase contains no domain name by design.
* A formal trademark search was not done. The name availability checks recorded earlier cover registries and package indexes, not trademark offices.

## Package

The project lives in this folder as a git repository with logical commits. A zip archive of the project, without dependency folders or build output, sits next to this folder as pointgoblin.zip.
