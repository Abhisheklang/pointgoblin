# PointGoblin Redesign Report

Date: 24 November 2026. Scope: visual redesign only. The backend, the API contracts, the user flows, the tests and the load numbers from BUILD_REPORT.md are unchanged and were retested, not rebuilt. This report supersedes the design, logo, screenshot and recording sections of BUILD_REPORT.md.

## Why this happened

The delivered design was rejected by the owner as AI slop, with an order to research Dribbble or another design site first and then fix everything. The honest diagnosis of the rejected design: a flat very dark green background, a generic hero headline, a numbered list, three plain cards on the landing page, and generic dark panels in the room. Nothing in it could only have come from this product.

## Research, sources actually read

Dribbble, read through its listing and profile pages:

* Poker skill listing, with shots including Poker App Concept by the Ronas IT team, Online Poker App Design, Poker Game Landing Page and WPT Poker Redesign. https://Dribbble.Com/skills/poker
* Agile development listing, with Planning Poker Extension, Scrumbs team screens and Sprint Planning. https://dribbble.com/search/agile-development?color=0a2e5c
* Dark mode tag page, with Bento Pro dark mode, Untitled UI settings and dark project cards. https://dribbble.com/tags/dark-mode
* Poker art listing, with EstimateQuest, described as planning poker with a retro twist, and Planning Poker / Scrum Poker Cards by Marcel Bechler. http://dribbble.com/search/poker%20art
* Online card game listing, with Scrum Card Game web app design by Denis Shapovalov and several card game UI kits. https://dribbble.com/search/online%20card%20game
* Designer profile of Mikalai, which lists two shots named Planning poker application for scrum teams. https://dribbble.com/miksush
* Search results for the Scrum Poker App by Paul Macgregor, 103 likes and 11.8k views, and for Poker planning cards by Samy Menai, 7.6k views.

One limit, stated plainly: individual Dribbble shot pages would not load in the research fetcher. The shot page for the Mikalai planning poker piece returned an empty body with status 202. Shot level conclusions therefore rest on listings, profiles, view counts and the case write ups below, never on shots that could not be opened.

Case write ups, read in full:

* Scrummer planning poker on Behance, branding and character illustration for a planning poker app, flat colour and playful cards. https://www.behance.net/gallery/52698401/Scrummer-planning-poker-IOS-app?locale=en_US
* Planning Poker by Jannik Pongratz, with a consensus stamp at reveal, a table that reflows as people arrive, and lowest, highest and average called out. https://pngrtz.com/projects/planning-poker
* Planning Poker at yunkhngn.dev, a real time scrum estimation tool with anonymous join, dark and light themes and instant invite. https://yunkhngn.dev/work/planning-poker

Awwwards, read:

* Studio K95, Site of the Day, a dark editorial portfolio with graphic design, motion and interaction, scored 7.32. https://www.awwwards.com/sites/studio-k95-3
* Kononenko Architectural Bureau, Site of the Day, minimalism, bold typography and thoughtful structure. https://www.awwwards.com/sites/kononenko-architectural-bureau
* A style analysis of Awwwards itself: ink #222222, paper white, canvas #E9E9E9, one ember accent #FA5D29 used as small colour blocks, Inter Tight doing all typographic work. https://stylr.dev/styles/awwwards
* A roundup of 2026 award winners, where the pattern that repeats is editorial, magazine grade art direction with oversized typography. https://hireadrian.com/award-winning-websites/

Palettes, read:

* ColorHunt dark palettes page opened, but its filtered grid returned no results in the text fetch. Palette values below come from ColorHunt palettes mirrored with full hex codes, and from a dark green palette collection. https://colorhunt.co/palettes/dark
* ColorHunt Kabocha Green set: #044A05, #2F5F3A, #1F75FF, cream #E7E7E3. https://colorswall.com/palette/286254
* ColorHunt Greyish Green and Cream Filling: #82A67D, #F47983, #989192, #F5F1DA. https://colorswall.com/palette/331944
* Dark green palette collection: Forest Velvet #0B3D2E, #145A3A, #2F7D5B, #CBbFA6; Evergreen and Cream #103B2F, #1F5A45, #3F8068, #F3EFE6, brass #B88A5A; Heritage Library #0F2F24, #254B3A, #6A5A43, #D1C2A6; Botanical Noir #06261D, #0E3B2C, #1F6F54, #E8D9C5, #8A2F2F. https://www.media.io/color-palette/dark-green-color-palette.html
* Coolors popular palettes page opened. Its palette grid did not render in the text fetch, so no Coolors palette is quoted here. https://coolors.co/palettes/popular

## Candidate directions

1. Casino felt, modernised. Felt #0B3D2E, table green #145A3A, brass #B88A5A, cream #F3EFE6, condensed grotesk display type. Drawn from the Dribbble poker game shots. Strong motif, but it keeps the product inside the dark green world that was just rejected, and casino cues fight the trust value.
2. Bento dark mode. Near black #101214, panels #17191C, leaf #6A994E, paper text #F2F0E8, Inter Tight throughout. Drawn from the Dribbble dark mode tag page. Competent and current, and exactly the generic dark dashboard family the brief forbids reheating.
3. Retro quest. Cream #F5F1DA, signal pink #F47983, sage #82A67D, ink #2B2B26, chunky retro display type. Drawn from the EstimateQuest shot and the ColorHunt cream palette. Memorable, but the joke would outgrow the tool and damage the professional trust value.
4. Botanical noir. #06261D, #0E3B2C, #1F6F54, cream #E8D9C5, oxblood #8A2F2F, high contrast serif. Rich and grown up, still dark, still a close cousin of the rejected palette.
5. Broadsheet at the felt table. Chosen. Paper #F7F2E2, parchment #EFE6CC, card white #FFFDF4, ink #152A1E, evergreen #17573A, deep felt #0D3524, leaf #6A994E, brass #CE9F3E, deep brass #A67C2E, clay #BC5837, rule line #D9CFB2. Fraunces for display type, Inter Tight for interface text, IBM Plex Mono for labels, codes and the deck strip.

## Why direction five

It inverts the rejected design instead of recolouring it: warm paper instead of dark panels, ink rules and hard offset shadows instead of soft dark cards, editorial serif headlines instead of a generic sans hero. Green survives only where it means something, as ink, as evergreen actions and as the felt of the table itself. Brass is rationed to the reveal moment, the way the Awwwards style analysis rations its single accent. The two visual motifs come from the product and nowhere else: a fan of cards spread from one point, and the table the team sits at. The consensus stamp is borrowed from the Pongratz case study because it turns agreement into an object a team can picture.

## What changed, screen by screen

Landing page. A broadsheet front page. A mono kicker, an oversized Fraunces headline in two voices (roman, then italic evergreen), and a pure CSS fan of five cards with a rotated agreement stamp. Below, a scrolling deck strip carries the full deck as a ticker. How a session runs is now an editorial table with oversized serif numerals and hairline rules. Why hidden votes sits on a parchment band as three columns divided by ink rules, with mono value labels for fairness, consensus and speed. Questions keep their content and gain print styled accordions. The footer is a deep felt band. All meta, open graph and structured data are unchanged, and the page is still fully static HTML.

Create and join. The same forms and the same logic, rebuilt as a printed table card with an ink border and a hard shadow. Tabs read as two card faces. The left column carries the headline Cards down. Numbers honest., three numbered editorial rows, and the deck strip. Labels are mono kickers. Inputs sit on paper with a brass focus outline.

Room. The room is now a table, literally. People and the story queue live in print cards on paper, with host marked by a brass avatar and a stacked label, and voted state shown as a tiny face down card. The voting stage is a deep felt panel: the story as a cream serif headline, seats as a row of chips with card pips that fill brass as votes land, and the deck as physical white cards that tilt like a held hand and straighten on hover. The selected card turns brass.

Results. A print card headed The reveal, with the average as an oversized Fraunces numeral and agreement as a rotating circular stamp that lands with a stamp animation. Individual votes flip in with the existing rotateY reveal, staggered, on paper cards with mono names.

Motion. The token system survives with the same durations (120 ms, 200 ms, 450 ms) and one easing family, transform and opacity only. New: the deck strip ticker, deck card tilt and straighten, stamp landing, and the fan on the landing page is static by design so the hero never moves under the reader. Reduced motion still switches animation off everywhere, including the ticker.

## Logo decision

Old mark: three cards rotated around separate centres at 14 degrees, a lime front card #8BD450 with a dark diamond, wordmark in Inter bold with a lime second half. It belonged to the rejected palette and its fan read as three loose rectangles.

New mark: the same concept family, redrawn. Three cards now fan from a single pivot point near the base, which is the convergence idea made literal: many cards, one point. The front card is evergreen with a cream diamond and an ink pip. The goblin ear survives, smaller, and moves to brass so it reads as the one playful accent. Back cards are card white with evergreen outlines, so the mark works on paper and on felt. The wordmark is Fraunces bold with Goblin in italic evergreen, matching the headline voice. The set is unchanged in scope: colour mark, primary lockup, lockup for dark felt, one colour version, favicons at 16, 32, 48, 180, 192 and 512 pixels, all regenerated from the new vector source. The logo sheet screenshot was recomposed tightly around the set, with size steps at 72, 40 and 20 pixels and no dead space. No brand document file was created, per the owner rule. This section is the logo record.

Values check, element by element. Fairness: the front card still shows no number, only the pip. Consensus: three cards, one pivot, one point. Speed: the fan is a single gesture, readable at 20 pixels. Mischief: the brass ear, kept small. Trust: flat geometry, a strict grid, no effects.

## Verification, rerun after the redesign

* Backend test suite: 26 passed, 0 failed. The backend code did not change.
* Lint and format: ESLint clean, Prettier clean, Ruff and Black clean. TypeScript compiles under strict mode and the production build passes.
* Responsive gate, same method as the first build, a real browser comparing document scroll width with client width on every screen at every width, with the new animation system in place: landing 4 of 4, create and join 4 of 4, room 4 of 4. Total 12 of 12, zero horizontal overflow. The deck shows all ten cards inside the viewport at 360 pixels.
* Live stack: earlier in this session the full stack ran on local PostgreSQL 16 and Redis 7 with two API instances, and the cross instance proof passed on the final backend code (a guest vote on instance two reached the host on instance one, room U4JXK9). The redesigned browser flow was driven end to end three times during screenshot verification and once more for the recording.
* Two defects found by looking at the new screenshots, both fixed and reshot: the host label in the presence list truncated long names, and the word Pass overflowed its card at phone widths. The deck numeral size now steps down on small screens.

## Rule gates, rechecked on the final tree

1. Brand domain pattern across the tree: 0 hits. Code and copy use localhost and relative addresses only.
2. Em dash and en dash characters: byte scan of all 68 text files in the tree, 0 and 0. Binary media files are excluded from the scan because compressed video bytes are not characters. Prose in the new copy was written without dash punctuation, using commas, colons and periods.
3. Leftover task markers and placeholder filler: 0 in source and copy. The single match for the marker words in the whole tree is the sentence in BUILD_REPORT.md that describes that search itself.
4. Console logging in the frontend: 0.
5. Third party product and company names in copy: none. Font and library names appear only as technical identifiers in code and package files.

## Media, replaced

Screenshots, all captured from the real running app in the new design, same descriptive file names as before:

* planning-poker-online-landing-page-desktop.png
* planning-poker-online-landing-page-mobile.png
* planning-poker-room-voting-in-progress-desktop.png
* planning-poker-room-votes-hidden-before-reveal.png
* planning-poker-results-average-and-agreement-desktop.png
* planning-poker-room-voting-deck-mobile.png
* pointgoblin-logo-set-on-dark-and-light-backgrounds.png

Recording, one continuous take of the same real host plus guest session on a two pane stage: landing page in the guest pane, host creates the room, guest joins by code, story added, both vote in secret, host reveals, results with the stamp. The new master is 56.4 seconds at 1920 by 1080, with the 1280 by 720 light copy beside it. Frames at 5, 25, 45 and 54 seconds were inspected: the room creation, the join, the hidden votes and the reveal all read correctly, and the logo is visible in both headers throughout.

* pointgoblin-planning-poker-live-demo-1080p.mp4
* pointgoblin-planning-poker-live-demo-720p.mp4

## Honest limits

* The working machine restarted midway through this session and its system packages did not survive. PostgreSQL and Redis were gone afterwards and the package manager was locked by another process, so the replacement recording was captured against a single API instance in the app's own local trial configuration (SQLite database, in memory event bus). The PostgreSQL and Redis proofs from earlier in the session stand as recorded above, and no backend code changed after them. The recording shows the same product flow either way, because both panes talk to one instance through the same proxy the development server always used.
* Docker Compose was still not run. Docker is not installed on this machine. The Compose file is unchanged by the redesign.
* Display fonts load from a public font service at runtime. Serif and sans fallbacks are declared everywhere, so a fully offline run keeps the layout and loses only the exact letterforms.
* Dribbble research limits are stated in the research section. Nothing in this report claims a shot was studied that the fetcher could not open.
* Nothing was published, deployed or registered. Local only, as ordered.
