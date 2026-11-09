# Small-Game Design Patterns (Fun / Replayable / Viral) and Feasibility of Solo AI-Assisted Development (2025–2026)

Research date: 2026-11-09. Some sources could not be fetched because they are outside this session's network allowlist (videogameschronicle.com, feedbagel.com), so a few points rely on search-result summaries rather than full page reads. Those are marked "(search summary)". Items from before 2025 are marked [older].

## Q1. What design patterns do successful small games (Balatro, Vampire Survivors, Brotato, Suika Game, Buckshot Roulette, Block Blast) share?

### Takeaway
The breakout small games share six traits. Rules fit in one sentence, often a twist on something players already know (poker, roulette, Tetris-style blocks, merging). Runs are short and can end suddenly. Randomized choices stack into "broken" synergies. Escalating numbers and effects give the feedback. Unlocks between runs keep players coming back. The price or entry cost is very low. Several were made by a single developer with a modest art budget, which shows that systems design and game feel matter more than art fidelity. I found no primary GDC postmortem for Balatro, Vampire Survivors or Brotato in this session. Most of the design evidence comes from interviews and secondary analysis.

### Cited Findings
**Balatro (LocalThunk, solo; Feb 2024)**
- It passed 5 million units sold about 11 months after its February 2024 launch. It went from 3.5M to 5M in roughly six weeks after its Game Awards nomination. — [Gematsu](https://www.gematsu.com/2025/01/balatro-sales-top-five-million); [Game World Observer](https://gameworldobserver.com/2025/01/21/balatro-another-1-5-million-copies-total-5m-units)
- The mobile version had earned over US$9M in in-app revenue by January 2025. — [Statista](https://statista.com/statistics/1546856/balatro-global-unit-sales) (search summary)
- Design lineage: a familiar ruleset (Big Two / poker hands) combined with the roguelike Luck Be a Landlord. Development started in late 2021. LocalThunk avoided playing similar games during development so they wouldn't shape the design. — [Game Informer interview, 2024](https://www.gameinformer.com/interview/2024/03/21/balatro-was-almost-called-joker-poker-and-other-details-from-its-creator) [older]; [GamesRadar](https://www.gamesradar.com/exploring-balatros-hype-its-ingenious-twists-on-poker-and-its-mysterious-creator) [older]
- LocalThunk realised the game was special when a friend reported playing it for 20–40 hours. Playtesting by people who keep playing was the validation signal. — [PC Gamer](https://pcgamer.com/games/roguelike/localthunk-had-made-hobby-games-in-the-past-but-realized-balatro-was-something-special-when-a-friend-revealed-he-had-played-it-for-20-30-or-40-hours)
- Meta-progression: jokers and vouchers unlock through in-game achievements and carry into future runs. Collection goals (gold stickers) and high-risk builds ("glass cannon") give long-term goals. — [saschb2b game-mechanics analysis](https://saschb2b.github.io/game-mechanics/games/balatro/design-tensions) (fan analysis)
- Launch and marketing analysis credits four pillars: promotion with streamers, several demos released over time, repeated Steam Next Fest entries, and active community building. — [GIGAZINE, Feb 2025](https://gigazine.net/gsc_news/en/20250207-balatro-successful-launch-strategy)

**Vampire Survivors (poncle / Luca Galante, originally solo)**
- It has reached 27M+ players, and poncle now has 25+ staff and a publishing arm. — [GamesRadar](https://www.gamesradar.com/games/roguelike/vampire-survivors-developer-working-on-15-projects-not-15-games-after-the-hit-roguelike-reached-27-million-players-and-spawned-a-whole-subgenre/)
- An academic commentary argues the reward structure draws on Galante's earlier work in gambling-industry design (variable rewards, chests, level-up choices). It also says the game meets the needs for competence (power fantasy) and autonomy (build choice). — [University of Portsmouth blog](https://csd.docstore.port.ac.uk/news-events-and-blogs/blogs/popular-culture/vampire-survivors-how-developers-used-gambling-psychology-to-create-a-bafta-winning-game)
- poncle reuses assets, systems and design principles across projects (e.g. the spin-off Vampire Crawlers) instead of building one large sequel. — [gamedev.net](https://gamedev.net/news/4991-how-vampire-survivors-became-vampire-crawlers-six-lessons-from-building-a-game/)

**Buckshot Roulette (Mike Klubnika, solo)**
- It launched on itch.io on 2023-12-28 at about $1.20 and came to Steam on 2024-04-04 at $2.99. — [GamingOnLinux](https://gamingonlinux.com/2024/04/buckshot-roulette-hit-a-million-sales-multiplayer-mode-in-development) [older]; [Windows Central](https://www.windowscentral.com/gaming/one-of-last-years-best-pc-games-just-came-to-steam-and-its-cheaper-than-a-cup-of-coffee)
- It passed 8 million copies sold by December 2025 (4M in Dec 2024). An Xbox port is planned for 2026. — [KitGuru](https://www.kitguru.net/gaming/joao-silva/buckshot-roulette-hits-8-million-sales-console-port-gets-delayed/); [WN Hub](https://wnhub.io/news/finance/item-49663)
- Pattern: a known premise (Russian roulette) with a small item/bluff layer. It fits on a single table in a single room, so asset scope is tiny, and each round is a short, tense, clip-able reveal. (My inference from the game's structure.)

**Suika Game (Aladdin X)** [older, 2023]
- It went viral through Japanese streamers and VTubers (incl. Hololive) from May 2023, then globally in September 2023 via Twitch streamers (Ludwig, LilyPichu). Sales rose "more than 50,000 times" compared with before it went viral. — [AUTOMATON](https://automaton-media.com/en/news/20231005-22096/); [Wikipedia](https://wikipedia.com/wiki/Suika_Game); [Sportskeeda](https://www.sportskeeda.com/esports/what-suika-game-viral-game-explored-popular-streamers-like-valkyrae-sykkuno-playing)
- Aladdin X credits "cute and friendly art that appeals to a wide audience" and simple rules. Physics-driven near-misses and sudden losses make streamer reactions entertaining to watch. — [Japan Times](https://www.japantimes.co.jp/business/2023/12/25/tech/suika-game-aladdin-x); [Pocket Tactics](https://www.pockettactics.com/suika-game/trend)
- It passed 4 million downloads on Switch. — [Shacknews](https://shacknews.com/article/137892/suika-game-nintendo-switch-4-million)

**Block Blast (Hungry Studio; mobile F2P)**
- It was the most downloaded mobile game of 2025 at 356.2M downloads (AppMagic), and it ranked #1 worldwide by downloads in Jan and Feb 2026 (Sensor Tower, via a company release). — [PocketGamer.biz](https://www.pocketgamer.biz/the-most-downloaded-mobile-games-of-2025); [mobilegamer.biz](https://mobilegamer.biz/the-top-mobile-game-downloads-of-2025/); [Business Wire](https://www.businesswire.com/news/home/20260312302688/en/Hungry-Studios-Block-Blast-Reinforces-Its-Position-Among-the-Free-Mobile-Games-Players-Turn-to-Most)
- Revenue is almost entirely from ads. Udonis estimates lifetime IAP at about $66K and ad revenue at about $584K/day. Third-party DAU figures vary widely (14M to 70M), so treat them as unverified. — [Udonis](https://www.blog.udonis.co/statistics/block-blast); [FoxData](https://foxdata.com/jp/blogs/block-blast-hits-puzzle-game-14m-dau-globally/)
- Stated appeal: intuitive "drag–match–clear" play, low pressure, short sessions, offline play. — [Block Blast news](https://www.blockblast.com/news/reinforces-free-mobile-games)

**Brotato (Blobfish, solo):** this session's searches returned no usable primary data on its sales or design. See Gaps.

### Inferences
- Common recipe: (1) a familiar base rule or theme; (2) a 1–20 minute run with a clear fail state; (3) 3-choice upgrade picks that create synergy combos and "broken build" moments; (4) escalating numeric/visual feedback; (5) permanent unlocks to drive "one more run"; (6) a low price ($1–$10) or free entry; (7) a demo or free web version to seed streamers.
- Three of these hits (Balatro, Vampire Survivors, Buckshot Roulette) used deliberately limited or lo-fi art: pixel/CRT card art, recolored sprite sheets, low-poly. A simple, consistent style was enough. Their success did not depend on art volume.
- Block Blast shows a separate path for mobile hypercasual: a zero-learning-curve puzzle with ad monetisation. It needs far less content but depends on user-acquisition (UA) and ad tuning, which is harder for a solo beginner to win.

### Gaps
- I found no primary GDC talks or written postmortems for Balatro, Vampire Survivors or Brotato in this session. The search surfaced the Game Maker's Notebook podcast with LocalThunk (https://gamemakersnotebook.libsyn.com/balatro-creator-localthunk-talks-inspirations-and-jokers), but I did not review it.
- The classic "juice" reference, the GDC Europe 2012 talk "Juice it or lose it" (Jonasson & Purho) [older], is from my background knowledge and its URL was not verified this session. The report writer should treat it as an unverified reference.
- No Brotato sales or design data was retrieved.

## Q2. What makes a game spread on TikTok / YouTube Shorts / Twitch in 2025–2026?

### Takeaway
In 2025 the dominant viral pattern was the "friendslop" co-op game: cheap, low-fidelity, physics-driven, chaotic multiplayer (Peak, R.E.P.O., Schedule I, Gamble With Your Friends). Its 15-second moments of unexpected failure are designed to be clipped. Single-player hits spread through readable "tension → reveal" moments (Suika's near-miss, Buckshot's trigger pull, Balatro's score explosion). The best viral metric is how shareable a moment is, not playtime.

### Cited Findings
- Medal's 2025 virality report says games like R.E.P.O., Peak and Lethal Company lead in virality (clip sharing) even when they aren't top "most played" titles. Schedule I scored 989k on Medal's metric. — [Business Wire / Medal report, Sep 2025](https://www.businesswire.com/news/home/20250912320056/en/National-Video-Game-Day-Report-Reveals-Top-25-Most-Viral-Games)
- Peak (June 2025) sold 2M+ copies in two weeks after going viral on TikTok and X. Its two small studios didn't expect the breakout ("ready to … go into vacation mode"). — [GamesRadar](https://www.gamesradar.com/games/survival/peak-put-friendslop-on-the-map-in-2025-but-neither-of-its-2-studios-expected-it-to-blow-up-we-were-ready-to-hit-the-launch-button-and-go-into-vacation-mode)
- AppMagic's Steam estimates for 2025: R.E.P.O. about 18.5M copies, Peak about 15.4M, Schedule I about 9.1M. These are single-source estimates. — [AppMagic blog](https://appmagic.rocks/blog/friendslop-steam-games-2025)
- Gamble With Your Friends sold 1M copies in one week (2026), which PC Gamer framed as friendslop's "total cultural victory". — [PC Gamer](https://www.pcgamer.com/games/puzzle/friendslop-approaches-total-cultural-victory-as-co-op-hit-gamble-with-your-friends-sells-1-million-copies-in-one-week/)
- Industry commentary says low-fidelity social chaos produces short, funny 15-second clips that spread on TikTok, Shorts and Discord. — [GamesMarket](https://www.gamesmarket.global/the-rise-of-friendslop-why-low-fidelity-social-chaos-is-shaking-up-the-games-industry/)
- Suika [older]: streamer and VTuber play drove the spread, and watchability came from near-wins and sudden losses. — [AUTOMATON](https://automaton-media.com/en/news/20231005-22096/)
- Balatro's launch used streamer promotion plus repeated demos and Next Fest entries. — [GIGAZINE](https://gigazine.net/gsc_news/en/20250207-balatro-successful-launch-strategy)

### Inferences
- Shareable-moment checklist: (a) understandable in 3 seconds with no explanation; (b) a visible tension build-up with a binary payoff, such as a fall, explosion or score spike; (c) physics or emergent chaos so every clip differs; (d) a free web demo or cheap price ($3–$8) so viewers can try it right away; (e) proximity voice or social betrayal in co-op titles.
- Co-op multiplayer helps virality but is risky for a solo beginner: netcode, servers and the need for a critical mass of friends. Single-player games with "absurd score explosion" moments, or turn-based games with a dramatic reveal, are more feasible.

### Gaps
- No primary TikTok, YouTube or Twitch data on game-clip performance in 2026 was retrieved. The friendslop sales figures are third-party estimates.

## Q3. AI-assisted / "vibe-coded" games that earned money or went viral (2025–2026), and how players reacted to AI art

### Takeaway
The flagship monetised vibe-coded game is Pieter Levels' fly.pieter.com (Feb 2025). Its revenue came from in-game ads and sponsorships sold to his large X audience, not from game sales, and the figures are founder-reported. Vibe Jams (2025: about 1,000–1,170 entries, ≥80% AI-written code; 2026 edition: $40K prizes) show AI coding can ship playable web games quickly. Players accept AI coding but are hostile to visible AI art. Disclosed AI use correlates with fewer reviews in some analyses, and accusations alone (even false ones) have triggered review bombs.

### Cited Findings
**fly.pieter.com and vibe jams**
- Levels says the game reached $1M ARR in 17 days, built with AI (Cursor/Claude) as a browser multiplayer flight sim (Three.js + Python websockets). — [levels.io](https://levels.io/full-multiplayer-python-websockets-game-ai) (founder-reported)
- Reported milestones: about $38K MRR by day 10 and $87K by day 17, mostly from selling in-game ad placements (blimps, planets, billboards). — [VGTimes](https://vgtimes.com/tech-and-hardware/122582-dutch-startup-founder-creates-game-using-ai-in-180-minutes-and-earns-87000-in-one-month.html); [404 Media](https://www.404media.co/this-game-created-by-ai-vibe-coding-makes-50-000-a-month-yours-probably-wont/)
- 404 Media's critique (headline "…makes $50,000 a month. Yours probably won't") argues the revenue depended on Levels' existing audience, not the game itself. — [404 Media](https://www.404media.co/this-game-created-by-ai-vibe-coding-makes-50-000-a-month-yours-probably-wont/)
- A later secondary source claims about $138K/month by November 2025. This is unverified. — [Sorceress blog](https://sorceress.games/blog/real-vibe-coding-apps-what-indies-built-in-2026)
- Vibe Jam 2025 rules: web-based, free, no login, multiplayer preferred, and at least 80% of code written by AI. The official site says "1000+ games entered", while Indie Hackers says 1,170. — [vibej.am/2025](https://vibej.am/2025); [Indie Hackers](https://www.indiehackers.com/post/2NUIOp80SUWuPmmfKoS9)
- Second place in 2025 was "Vibeware" by @mattgordonxyz ($5,000). I could not confirm first place; Great Taxi Assignment: Vibe City was widely praised. — [vibej.am/2025](https://vibej.am/2025); [playonray](https://playonray.com/blog/levelsio-vibe-jam-winners-ray-vibe-awards)
- An iOS developer reportedly won $25,000 with a vibe-coded capybara game. — [Wccftech](https://wccftech.com/ios-developer-made-capybara-game-using-vibe-coding-and-won-25000/)
- 2026 edition (Cursor Vibe Jam): $40K prize pool. About 1 in 7 multiplayer entries used the Colyseus framework. — [vibej.am 2026 press](https://vibej.am/2026/press); [Colyseus blog](https://colyseus.io/blog/vibe-jam-2026/)

**AI on Steam: scale and sales effect**
- About 7,818 Steam titles disclosed generative-AI use in 2025, roughly 1 in 5 new releases (about +700–800% YoY) and about 7% of the whole library. — [Tom's Hardware](https://www.tomshardware.com/video-games/pc-gaming/1-in-5-steam-games-released-in-2025-use-generative-ai-up-nearly-700-percent-year-on-year-7-818-titles-disclose-genai-asset-usage-7-percent-of-entire-steam-library)
- About 20% of Steam's top 100 new releases in 2025 used generative AI, but fewer than half of them disclosed it. Examples include Escape From Tarkov (background/shout-out art) and The Alters (subtitles, placeholders). — [eTeknix](https://www.eteknix.com/nearly-20-of-steams-2025-top-sellers-used-ai/)
- Another analysis says only 8% of 2025 top sellers disclosed AI. The two figures measure different things. — [RaiderKing](https://raiderking.com/only-8-of-steams-2025-top-sellers-disclosed-generative-ai-use/)
- Game Oracle analysis: AI-disclosed games get significantly fewer reviews. A follow-up that controls for launch month finds the per-game effect roughly flat, and flopped AI games mention art/textures more often. — [Digital Citizen](https://www.digitalcitizen.life/steam-games-that-disclose-ai-use-may-sell-far-less-new-study-finds/); [fragwyz Substack](https://fragwyz.substack.com/p/three-years-of-ai-on-steam) (search summary)
- My Summer Car (2.5M+ sold) disclosed a few AI-generated paintings. This is an example of minor AI use in a hit. — [eTeknix](https://www.eteknix.com/nearly-20-of-steams-2025-top-sellers-used-ai/) (search summary)

**Player backlash cases**
- Shrine's Legacy (late 2025) got AI-accusation reviews, which were refuted (the cited image was an April Fools' post). — [PC Gamer](https://www.pcgamer.com/games/rpg/rpg-dev-pushes-back-against-steam-review-ai-accusations-we-poured-years-of-our-lives-into-this-game-and-only-worked-with-real-human-artists-on-everything)
- PC Gamer's "a touch of AI is all it takes to trigger backlash" column covers a promising indie hit by "slop skeptics". — [PC Gamer](https://www.pcgamer.com/gaming-industry/steam-week-in-review-a-touch-of-ai-is-all-it-takes-to-trigger-backlash-as-a-promising-new-indie-falls-afoul-of-slop-skeptics/)
- Vapor World replaced in-engine cutscenes with AI video and drew backlash. — [Everything Edinburgh](https://everythingedinburgh.com/games/news/vapor-world-steam-ai-cutscene-backlash/)
- The solo developer of "Hardest" said they would delete the game from Steam over its AI assets. — [FinalBoss](https://finalboss.io/dev-will-delete-steam-game-hardest-over-ai)
- Heartopia drew criticism for AI-written letters ("makes the whole experience feel hollow"). — [LODJ](https://www.lodj.ma/The-Soul-vs-The-Machine-Heartopia-Faces-AI-Revolt_a159068.html?print=1)
- Recreate Games / Party Animals (2026) were review-bombed after announcing a $75K AI video contest. — [pulse.bot](https://www.pulse.bot/gaming/news/recreate-games-apologizes-after-75000-ai-video-contest-triggers-steam-review-bomb-e3f49945-b413-4290-a702-70564e6bbabb/)
- Developers say "AI slop" has become an insult thrown around without evidence. — [Creative Bloq](https://creativebloq.com/ai/ai-slop-has-become-a-harmful-insult-hurled-around-with-no-evidence-game-developers-claim)
- Over 500 Steam Next Fest games used AI, which disappointed players. — [Gamepressure](https://www.gamepressure.com/newsroom/steam-next-fest-severely-disappointed-players-more-than-500-games/z08800)
- AI-generated capsule art is criticised as making Steam browsing worse. — [feedbagel (PC Gamer review summary)](https://feedbagel.com/post/spammy-ai-generated-steam-capsule-art-is-a-pox-and-it-makes-browsing-less-fun) (search summary)

### Inferences
- Code written with AI tools (Claude Code, Cursor) is effectively invisible to players and, since January 2026, does not need disclosing on Steam (see Q5). The reputational risk sits almost entirely in visible or audible assets: art, voice, writing, store capsule art.
- fly.pieter.com's success depended on audience distribution plus an ad/sponsor model. A beginner without an audience should not expect to repeat it. The transferable lesson is to ship a free, instantly playable browser build, add sponsor or ad slots, and build in public.
- Safer posture: use AI heavily for code and prototyping, keep player-facing art human-made or heavily human-edited (or use a deliberately abstract style), and disclose honestly. Avoid AI store/capsule art, which signals "slop".

### Gaps
- Fetching the full Game Oracle and feedbagel studies failed (host not allowed). Their methodology is unverified.
- I found no verified example of a commercially successful Steam game whose main art was mostly AI-generated and was well received.

## Q4. Practical limits of AI image generation for game assets, and workarounds

### Takeaway
As of 2025–2026, AI image tools handle single static images well: card art, portraits, backgrounds, icons, item art, UI mockups. They are unreliable for frame-consistent sprite animation and for keeping one character on-model across many poses. Each generation drifts in proportion, palette and line weight, and pixel-art cleanup can take longer than drawing by hand. Genres that need lots of static illustrations and few animations suit AI art best: card roguelikes, puzzle/merge, visual-novel-like, board/table games, and survivors-likes that use simple shapes. Character-animation-heavy action platformers suit it worst.

### Cited Findings
- Practitioner guides say tools are decent at static sprites but struggle with coherent animation frames. Generations are largely independent, so proportions, palettes and line weight drift. Suggested fixes: restrict the palette, apply uniform outlines, and colour-correct afterwards. — [Relish Games journal](https://relishgames.com/journal/generative-ai-for-2d-game-art-tools-and-techniques/); [Makko blog](https://blog.makko.ai/ai-game-art-generator/)
- AI sprites usually need manual cleanup in Aseprite/Piskel, and for some developers this takes longer than drawing from scratch. A more reliable route is AI keyframes followed by interpolation or manual cleanup. AI animation is mainly useful for prototypes and placeholders. — [freegamesprites (2026)](https://freegamesprites.com/news/ai-pixel-art-generation-2026-tools-and-workflows); [DEV Community](https://dev.to/1213181051/i-got-tired-of-drawing-24-frames-for-every-run-cycle-so-i-built-an-ai-tool-to-generate-2d-sprite-3oig)
- Vendors (Layer.ai, Ludo.ai sprite generator) claim style-training fixes drift. A 2026 claim says GPT Image can make "a full sprite sheet from one reference". These are vendor or promotional claims, not independent evidence. — [Layer.ai](https://www.layer.ai/use-cases/sprite-generation); [App Developer Magazine (Ludo.ai)](https://appdevelopermagazine.com/ludo.ai-debuts-sprite-generator-for-instant-2d-animation-creation/); [Indie Hackers](https://www.indiehackers.com/post/gpt-image-2-5-a-full-sprite-sheet-from-one-reference-110562d19f); [PCTechMag (Jul 2026, promotional)](https://pctechmag.com/2026/07/cutting-sprite-production-time-from-weeks-to-minutes-without-losing-consistency/)
- Tool context: Higgsfield's toolset (available in this project) offers character-sheet workflows, reference "Elements" and Soul training for character consistency, plus image-to-3D (`generate_3d` → GLB) and a website/game-builder workflow. These are workarounds for the consistency problem, not guarantees. (From this project's CLAUDE.md and the MCP tool descriptions, not from an external source.)

### Inferences
Workarounds, ranked from most to least feasible for a solo beginner:
1. **Card-art / illustration-heavy design** (Balatro-like, deckbuilders, tarot or fortune themes): each card is a standalone still, so drift between images is acceptable as long as the frame, palette and border are unified in code or a template.
2. **Static art with programmatic juice**: animate in code (tweens, squash and stretch, particles, screen shake, shaders) instead of drawing frames. Buckshot Roulette and Balatro get most of their feel from motion and effects, not frame-by-frame animation.
3. **Abstract or geometric styles** (Block Blast, Suika-style fruit, neon shapes): little to keep on-model.
4. **Character reference sheet + limited poses** (front, idle, hit) generated with reference images, then palette-locked and hand-cleaned.
5. **3D-to-2D**: generate a 3D model (image-to-GLB), rig and render it to sprites. This gives consistency, but rigging is a skill barrier.
6. Avoid: platformers or fighting games that need 8–24-frame run, attack and jump cycles for many characters.
- Audio: AI music (e.g. Suno) for BGM is low-visibility compared with art, but licensing is unsettled (Q5).

### Gaps
- I found no independent benchmark of sprite-animation consistency across tools, and no indie postmortem that measures AI-art cleanup time.

## Q5. Legal / policy: Steam AI disclosure, copyright status of AI assets, commercial-use terms

### Takeaway
Steam allows AI content but requires disclosure. Since January 2026 the form is narrower: it covers player-facing content (art, audio, text, localisation; pre-generated vs. live-generated), and AI coding tools and other internal efficiency tools are exempt. itch.io requires AI tagging, and untagged AI projects lose browse-page indexing. In the US, purely AI-generated output is not copyrightable (prompts alone are insufficient). Human selection, arrangement and modification can be protected. Paid plans of Midjourney and Suno grant commercial use, but ownership is limited and both companies face major lawsuits, so a game's AI assets carry IP-enforcement and reputational risk.

### Cited Findings
**Steam (Valve)**
- Disclosure has been required since January 2024 and appears on the store page as "AI Generated Content Disclosure". — [Tbreak](https://tbreak.com/steam-ai-disclosure-policy-update-developers/); [GIGAZINE, Jan 2026](https://gigazine.net/gsc_news/en/20260120-steam-updates-ai-disclosure-guidelines)
- January 2026 revision ("significantly rewritten"): developers no longer need to disclose AI-powered tools used for efficiency, such as code assistants, if no generated content ships in the game. Content players see or hear (art, music, narrative, localisation, marketing assets) must still be disclosed. The form separates pre-generated from live-generated content. Valve says the policy "is not focused on efficiency gains through the use of such tools". — [VGC](https://www.videogameschronicle.com/news/valve-has-significantly-rewritten-steams-rules-for-how-developers-much-disclose-ai-use) (fetch blocked; search summary); [Slashdot](https://games.slashdot.org/story/26/01/19/1735231/valve-has-significantly-rewritten-steams-rules-for-how-developers-must-disclose-ai-use); [GameMeca](https://www.gamemeca.com/en/view.php?gid=1770331); [GosuGamers](https://www.gosugamers.net/entertainment/news/77861-steam-revises-ai-policy-while-keeping-generative-content-disclosure-intact)
- Some coverage describes disclosure as largely self-reported and not actively enforced by moderation. Treat this with caution: live-generated content also requires guardrails against illegal content under Valve's original 2024 rules [older]. — (search summary of the sources above)
- Epic CEO Tim Sweeney argued (November 2025) that Steam should drop AI labels. — (from the backlash search summary; [Gamepressure](https://www.gamepressure.com/newsroom/discussion-about-ai-label-on-steam-continues-the-dev-is-being-pun/ze8ab3))

**itch.io**
- Since November 2024 [older], a mandatory generative-AI disclosure field gives projects "AI Generated" sub-tags (graphics, sounds, etc.) or a "No AI" tag. Hand-edited AI output still counts. Untagged AI projects are not indexed on browse pages, and enforcement relies on user reports. Reports disagree on whether the field is required for games or only for asset packs; a later report says it covers games too. — [PC Gamer](https://pcgamer.com/software/platforms/indie-distribution-platform-itch-io-now-requires-asset-creators-to-disclose-the-use-of-generative-ai-in-their-work); [Game Developer](https://gamedeveloper.com/production/itch-wants-asset-creators-to-disclose-when-they-ve-used-generative-ai); [GamesMarkt](https://gamesmarkt.de/development/itchio-now-requires-gen-ai-content-to-be-tagged-in-all-games-and-asset-packs-711e824843d410eab51fcd9436836294)

**US Copyright Office**
- Part 2 report (Copyrightability), published 2025-01-29: copyright requires human authorship. Using AI as a tool does not bar protection. Prompts alone do not give enough control to make the output protectable. Human-authored expression perceptible in the output, and creative selection, arrangement or modification, can be protected. Decisions are case by case, and no new legislation is needed. — [Copyright Office blog](https://blogs.loc.gov/copyright/2025/02/inside-the-copyright-offices-report-copyright-and-artificial-intelligence-part-2-copyrightability/); [Crowell](https://www.crowell.com/en/insights/client-alerts/us-copyright-office-releases-part-2-of-artificial-intelligence-report-clarifying-copyrightability-of-generative-ai-outputs); [Mintz](https://www.mintz.com/insights-center/viewpoints/54731/2025-02-07-us-copyright-office-publishes-second-part-report-ai)
- Implication for games: code, design, level layout and human edits are protectable. Raw AI sprites may be copyable by others without recourse. — (inference consistent with the above; also noted by [Relish Games](https://relishgames.com/journal/generative-ai-for-2d-game-art-tools-and-techniques/))

**Tool terms and litigation** (secondary sources; verify the current ToS)
- Midjourney: paid plans grant commercial use (free trial does not). Companies with more than $1M gross revenue must use Pro or Mega. No IP indemnification. Disney and Universal sued Midjourney on 2025-06-11 (C.D. Cal.), alleging it generated copyrighted characters; DreamWorks joined later. — [terms.law Midjourney guide (Jan 2026)](https://terms.law/2026/01/15/midjourney-commercial-use-rights-complete-2026-guide/); [licenseorg](https://licenseorg.com/blog/ai-commercial-use-guide-2026)
- Suno: Pro/Premier paid plans grant commercial use, and free-plan songs stay non-commercial even after upgrading. After the December 2025 terms update, paid users get a commercial license but are generally not treated as owners. Warner Music settled and partnered with Suno on 2025-11-25; UMG and Sony litigation continues. A German GEMA court ruling against Suno was reported but not verified here. — [Music in Africa](https://www.musicinafrica.net/magazine/suno-adjusts-ai-music-ownership-terms-after-warner-music-partnership); [terms.law Suno](https://terms.law/ai-output-rights/suno/); [findskill.ai (GEMA)](https://findskill.ai/blog/suno-gema-ruling-ai-music/); [Dynamoi timeline](https://dynamoi.com/learn/ai-music-distribution/ai-music-copyright-cases-timeline)
- Higgsfield commercial-use terms: not researched in this session (see Gaps).

### Inferences
- Lowest-risk stack for a solo beginner: AI for code (no Steam disclosure needed since January 2026); human-made or heavily human-edited art in a simple style; licensed or human-made audio, or AI audio on a paid plan with that limitation noted; honest disclosure of any shipped AI content. Never prompt for existing IP or characters. That is the core allegation in the Disney/Universal case, and Steam and app stores remove infringing content.
- Because raw AI assets are weakly protectable, clones of AI-art games are hard to stop. The defensible value is the systems, tuning and brand, which AI-assisted code does not weaken.

### Gaps
- I did not research Apple App Store or Google Play AI-content rules this session. As far as I know they have no Steam-style AI label, only general IP and spam rules ("minimum functionality", copycat/spam guidelines), but this is unverified.
- Web portals (CrazyGames, Poki) AI policies: not researched.
- Higgsfield's own commercial-use and ownership terms, and Japan's copyright position (Agency for Cultural Affairs 2024 guidance [older]), were not checked in this session and should be verified if the game targets Japan.
- I could not open the primary Steam announcement or VGC article. The details of the January 2026 form come from multiple secondary summaries that agree.
