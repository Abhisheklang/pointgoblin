# PointGoblin Repositioning Report

Date: 24 November 2026. Status: complete locally. Nothing was pushed to GitHub and no GitHub setting was changed in this work.

## Why this happened

The user objected that PointGoblin read like a product being sold. The word Free in the GitHub description, the banner tagline, and the site copy made a resume portfolio project feel like a commercial launch. The order that followed was a full repositioning: every public surface must read like an engineering project case study, because the project exists as evidence for job applications.

## Positioning now

PointGoblin is a backend portfolio project. Public copy states what was built, how it works, what was measured, and what its limits are. There is no sales structure anywhere: no marketing pitch, no benefit selling, no audience selling, no pricing style calls to action, and no use of the word free as sales language.

## Old structure versus new structure

Old landing page, a product site:

* Nav: How it works, Why hidden votes, Questions.
* Hero: a pitch headline, a paragraph describing a tool for scrum teams, and calls to action to start a room.
* A five step sales walkthrough of a planning session.
* A benefits section about fairness, consensus, and speed.
* A selling FAQ about planning poker.
* Footer line: Fair estimates for remote teams.

New landing page, a project case study, in the same Broadsheet visual identity (paper, ink, evergreen, brass, Fraunces):

* Nav: Overview, Live demo, Architecture, Load test, Run locally.
* First screen: the project name in the brand header, one factual line (a real time planning poker application built to demonstrate a production style backend), the key proof numbers as data (300 concurrent clients, 192 ms vote broadcast, 26 tests, 2 API instances), and entry points to the live demo and the load test section.
* Overview: what was built and why, including the anchoring background and the server side hidden vote rule.
* Live demo: a factual description of the working application and the four steps of a demo session. The application itself is unchanged in behaviour.
* Architecture: the request and event flow across browser, API, database, event bus, and second instance, followed by engineering decisions and trade offs (Redis pub sub across instances, broadcast coalescing, hidden state held on the server).
* Load test: method and a results table.
* Testing: the suite breakdown, the static gates, and the responsive checks.
* Known limits, stated plainly: Docker Compose not run in the build environment, fonts load at runtime, media captured in a trial configuration, no public deployment.
* Tech stack and Run locally sections.

## What was removed or rewritten, and why

* The sales walkthrough (How a planning poker session runs) became the Live demo section: same facts, written as a demo description instead of a pitch.
* The benefits section (Why hidden votes make estimates better) was removed as a selling block. Its technical content moved to Architecture, as the hidden state decision, and to Overview, as background on anchoring.
* The selling FAQ was removed from the landing page. Factual questions live in the README as Technical notes.
* The hero pitch headline (Every card face down. Then, all at once.) was replaced with a factual headline: Real time planning poker. Built as a backend project.
* The footer line (Fair estimates for remote teams) was replaced in the landing, the app entry screen, and the room screen with: PointGoblin. A backend portfolio project.
* The app header link and demo entry copy were reviewed; the working application flows (create, join, room, voting, reveal) are unchanged.

## Word level sweep, sales use of the word free

Removed, with replacements:

* GitHub About file and landing meta: Free online planning poker for remote teams, replaced with the portfolio description that the GitHub description already carries.
* Landing page title: Planning Poker Online, Free Scrum Estimation Rooms, replaced with PointGoblin, Real Time Planning Poker, a Backend Portfolio Project.
* Landing meta description and social description: a free online planning poker tool, replaced with a factual project description naming the stack.
* Landing structured data: the Free description was rewritten, and the price offer block (price 0) was deleted, because an offer is commerce markup.
* Landing eyebrow: Free planning poker, Remote teams, No sign up for guests, replaced with Real time planning poker, FastAPI, WebSockets, Redis.
* Landing hero paragraph: a free online planning poker tool built for scrum teams, replaced with the case study introduction.
* Landing call to action: Start a free room, replaced with Start a room, and later Open the live demo in the restructure.
* App entry kicker: Planning poker, Remote teams, Free, replaced with Real time planning poker, FastAPI, WebSockets, Redis.
* README opening: a free online planning poker tool for agile teams, replaced with the backend portfolio project framing, including the load test figure.

Kept, with justification:

* README, interview defence section: the event loop stays free for socket traffic. Here free means unblocked, a technical statement about the event loop, not a price claim. One hit, kept deliberately.
* Licence and dependency licence texts use free in the legal sense. Those files are not project copy and were left untouched.

## README changes

* Title now reads: PointGoblin: Real Time Planning Poker, a Backend Portfolio Project.
* The Why teams use planning poker section became Background, and what this project demonstrates, with a demonstration list tied to evidence in the repository.
* Features became What was built. How it works became How a demo session runs. Questions people ask became Technical notes.
* A Known limits section was added, matching the landing page.
* Architecture, load test results, and the interview defence material were kept and now sit inside a consistent case study framing from the first screen onward.

## Media, all captured from the real running application

Screenshots in screenshots/:

* planning-poker-online-landing-page-desktop.png, retaken at 1920 by 1080. New case study hero, proof numbers row, new nav.
* planning-poker-online-landing-page-mobile.png, retaken at 390 by 844.
* planning-poker-room-voting-in-progress-desktop.png, retaken. Host view, both votes in, before reveal.
* planning-poker-room-votes-hidden-before-reveal.png, retaken. Guest view of the same moment, values withheld.
* planning-poker-room-voting-deck-mobile.png, retaken at 390 by 844.
* planning-poker-results-average-and-agreement-desktop.png, retaken. After reveal: average 6.5, agreement 50 percent.
* pointgoblin-logo-set-on-dark-and-light-backgrounds.png, not retaken. The logo did not change and the sheet carries no sales copy, only labels for the lockups and marks.

Recording in recordings/:

* pointgoblin-planning-poker-live-demo-1080p.mp4, new, 45.8 seconds, 1920 by 1080, 2,444,095 bytes. Two windows side by side, host and guest, one continuous session: landing page, host sign in and room creation, guest joins with the code, story added, both vote with values hidden, host reveals, results on both windows.
* pointgoblin-planning-poker-live-demo-720p.mp4, light copy, 1280 by 720, 1,024,458 bytes.
* Frames at 5, 22, 38, and 44 seconds were inspected. The flow reads in order and the reveal lands on both windows.

Banner:

* pointgoblin-social-preview.png in the repo banners folder, regenerated from the new landing screenshot with the existing builder. 1280 by 640, 178,936 bytes. Tagline now reads: Real-time planning poker. A backend portfolio project. Inspected visually: no selling text is legible anywhere in the image, including inside the screenshot region.

## Gates, all rerun after the rewrite

* Backend tests: 26 passed, 0 failed (accounts 8, rooms 7, voting 8, live WebSocket 3).
* Frontend: ESLint clean, Prettier check clean, strict TypeScript production build succeeds.
* Backend style: Ruff clean, Black clean. Backend code was not changed in this work.
* Responsive: landing, app entry, and room checked at 360, 768, 1280, and 1920 pixels. 12 of 12 with zero horizontal overflow, measured as scrollWidth minus clientWidth on the live pages.
* Rule gates across the tree: brand domain pattern 0, em dash characters 0, en dash characters 0, TODO and FIXME 0, console.log in the frontend 0.
* Sales word sweep: grep for the word free across the landing HTML, the app entry HTML, the frontend source, the README, and the About file returns exactly one hit, the technical event loop sentence justified above.
* Capture configuration: the stack ran locally with SQLite and the in memory event bus (the trial configuration the test suite uses), with the Vite dev server in front of the API. The PostgreSQL and Redis verification from the original build is unchanged and stands.

## Commits

* 1455e54 Reposition PointGoblin as a backend portfolio project (landing page, app strings, README, About file).
* 1e83a3f Replace screenshots and recording with the repositioned site.
* This report is committed on top of those two. The final local head is reported with this delivery.

## Not done

* No push to GitHub and no GitHub settings were changed. The redeploy is handled separately, after this local work.
* Docker Compose remains unrun, for the same reason as before: Docker is not available in this environment.
