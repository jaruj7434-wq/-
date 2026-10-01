# Desert Duel — Seedance 2.5 作り直し版プロンプト(v3:冒頭2カット追加・24秒)

## 変更点(v2 → v3)
- 冒頭を2カットに: SHOT 01 男性の銃口アップ→男性へピント送り(0〜2秒)、SHOT 01B おばあさんの同じ構図→おばあさんへピント送り(2〜4秒)
- 以降は v2 と同じ構成で、時間を+2秒ずらした(全24秒)
- 顔の破綻対策: 二人を参照エレメントで指定+「顔を参照と完全一致」、冒頭2カットは静止画を参照に添付

## 生成設定
- モデル: `seedance_2_5` / mode `omni_reference` / 24秒 / 9:16
- 参照エレメント: 男性 `f264355d-…`、おばあさん `4f672ef6-…`
- 参照画像(順番): 1) 男性銃口 `9251d24a-…` 2) おばあさん銃口 `0c5af838-…` 3) おばあさん変身後 T3 `950cd934-…` 4) 男性変身後 T6 `2dfc5986-…`
- 費用(プレフライト): 480p 72 / 720p 168 / 1080p 288 クレジット

## Prompt
```
TITLE: "FASHION DUEL" — a 24-second vertical (9:16) photorealistic action-comedy short film.

LOGLINE
In a sunbaked desert, a young man and an elderly woman face off in a Western-style gun duel.
But the bullets don't hurt — whoever gets hit is instantly transformed into a brand-new,
head-to-toe fashionable outfit. It's a battle of who can make the other look cooler.
The grandmother wins: the young man's new look is so impossibly cool that he admits defeat
and faints face-first into the sand, while she blows the smoke off her revolver at the camera.

CHARACTERS — FACE LOCK: the faces must match the reference people EXACTLY in every shot,
including close-ups and fast motion. Do not beautify, age, reshape or swap the faces.
- THE YOUNG MAN = <<<f264355d-52eb-4665-9e9c-a58c36c62a47>>>. Always on the LEFT side of the frame, facing RIGHT.
  Before: his original horizontal-striped Breton shirt look.
  After (exactly the black outfit of the young man in the attached image of him in black):
  a long, sharply tailored black leather trench coat worn open, black high-neck knit,
  black wide-leg pleated trousers, polished black lace-up boots, layered silver chains and
  rings, slim black sunglasses — a runway-level look.
- THE GRANDMOTHER = <<<4f672ef6-b040-4eb9-b178-2cf69c5f931d>>>. Always on the RIGHT side of the frame, facing LEFT.
  Before: her original blue outfit.
  After (exactly the cream outfit of the grandmother in the attached image of her in cream):
  a cream-white tailored long coat, cream silk blouse, cream wide-leg trousers,
  patterned silk scarf, gold jewelry, tortoiseshell sunglasses pushed up on her head, white
  leather sneakers — quiet-luxury style.

WORLD & LOOK
- Vast desert with low dunes and scattered rocks, low late-afternoon sun from the LEFT,
  long shadows, drifting dust and tumbleweeds.
- Shot like a modern action movie: anamorphic 35mm look, warm amber highlights and teal
  shadows, subtle film grain, shallow depth of field, lens flares, speed ramps
  (slow motion into real time), whip pans, snap zooms and hard cuts on the beat.

DIALOGUE (spoken in Japanese, exactly as written)
- SHOT 06, the young man, before he fires: 「その服時代遅れだよ」
- SHOT 13, the grandmother, before she fires: 「本当のおしゃれを教えてやるよ」
- SHOT 18, the young man, just before he falls: 「カッコ良すぎる...」

CONTINUITY RULES (apply to every shot)
- The two characters always face each other and look at each other — never at the camera,
  except in the very last shot. (In the two opening muzzle shots only the gun points at the
  lens; their eyes look at their opponent.)
- Both always hold an antique Western revolver in their right hand.
- Never cross the 180-degree line: the man stays screen-left, the grandmother screen-right,
  even in over-the-shoulder shots.
- Gunfire looks real (muzzle flash, white smoke, recoil, a small brass bullet in flight),
  but every hit is completely harmless: no injury, no blood, no wound. On impact only the
  clothes change, spreading outward from the impact point like a wave, with a small puff
  of smoke.

SHOT LIST

[ACT 1 — THE STANDOFF: build tension]

SHOT 01 (0.0–2.0s) — Opening A: the man's muzzle, rack focus to the man
  Match the first attached image (the macro shot of the muzzle) exactly as the first frame.
  Macro extreme close-up: the muzzle of the young man's antique Western prop revolver points
  straight at the viewer — directly into the camera lens, dead center of the frame — in
  razor-sharp focus; behind it the young man is only a soft blurred shape. After about 0.8
  seconds the focus racks quickly from the muzzle to his face: the muzzle melts into blur and
  his face becomes sharp and clearly recognizable (exactly his reference face), eyes locked
  forward. Wind hisses. Hard cut.

SHOT 01B (2.0–4.0s) — Opening B: the grandmother's muzzle, rack focus to the grandmother
  The same composition mirrored for her, matching the second attached image: macro extreme
  close-up of the muzzle of her antique Western prop revolver pointing straight at the viewer,
  dead center, razor-sharp; behind it the grandmother in her original blue outfit is a soft
  blurred shape. After about 0.8 seconds the focus racks to her face: sharp, clearly
  recognizable (exactly her reference face), calm and fearless. Hard cut.

SHOT 02 (4.0–4.6s) — Extreme close-up: the man's eyes
  Profile, facing right. Eyes narrow. A single drop of sweat runs down his temple.
  Very slow push-in.

SHOT 03 (4.6–5.2s) — Extreme close-up: the grandmother's eyes
  Profile, facing left. Calm, unblinking, a hint of amusement. Very slow push-in.

SHOT 04 (5.2–5.7s) — Insert: the man's hand
  Macro shot of his fingers flexing and tightening around the revolver grip.

SHOT 05 (5.7–6.3s) — Insert: the grandmother's hand
  Macro shot of her wrinkled thumb pulling back the hammer. Sharp metallic click.

SHOT 06 (6.3–7.8s) — Close-up: the man's face, the line
  Low-angle close-up, slow push-in onto his mouth as he says in Japanese, with a cocky
  half-smile: 「その服時代遅れだよ」

SHOT 07 (7.8–8.4s) — Close-up: the grandmother's reaction
  One eyebrow slowly rises. The corner of her mouth curls into a knowing smirk.

[ACT 2 — FIRST SHOT: the grandmother's makeover]

SHOT 08 (8.4–9.0s) — Over-the-shoulder from behind the man: he fires
  His shoulder and gun arm in the left foreground, the grandmother in focus on the right.
  He pulls the trigger: bright muzzle flash, burst of white smoke, recoil kicks the gun up.
  Hard camera shake on the shot.

SHOT 09 (9.0–10.6s) — Bullet cam (slow motion)
  The camera flies alongside the spinning brass bullet in extreme slow motion, slowly
  orbiting around it as it cuts through glittering dust particles. The grandmother grows
  larger in the background. In the last frames the shot speed-ramps back to real time and
  snap-zooms toward her chest.

SHOT 10 (10.6–12.2s) — Impact and transformation (speed ramp)
  Medium-full shot. The bullet touches her chest — a tiny puff of smoke, she doesn't even
  flinch. From that point her blue outfit transforms outward like a wave into the cream-white
  luxury look. As the change spreads, the camera sweeps in a fast 180-degree arc around her
  (ease-out into slow motion), coat and scarf lifting in the wind. She stays facing left.

SHOT 11 (12.2–13.4s) — Fashion reveal tilt-up
  Low angle. The camera tilts up from her white leather sneakers, over the wide-leg trousers
  and long coat, to her scarf, gold jewelry and confident face, sunglasses resting on her head.
  She adjusts her scarf with her left hand, revolver still in her right.

SHOT 12 (13.4–14.0s) — Reaction: the man
  Quick close-up: his jaw drops. A snap zoom on his stunned eyes.

[ACT 3 — THE COUNTERSHOT: the man's makeover]

SHOT 13 (14.0–16.0s) — Close-up: the grandmother
  She looks straight at him and says in Japanese, calm and confident:
  「本当のおしゃれを教えてやるよ」

SHOT 14 (16.0–16.6s) — Reverse over-the-shoulder from behind the grandmother: she fires
  Her shoulder and gun arm in the right foreground, the man in focus on the left.
  Muzzle flash, white smoke, recoil. Camera shake.

SHOT 15 (16.6–17.6s) — Bullet cam (faster, reverse direction)
  The camera chases the bullet from behind, flying right-to-left with a quick barrel roll,
  then snap-zooms into the man's chest.

SHOT 16 (17.6–19.2s) — Impact and transformation (hero shot)
  Low-angle hero shot. A tiny puff of smoke at his chest — unhurt. The striped shirt
  transforms outward like a wave into the black runway look; the long leather trench coat
  unfurls and flares dramatically in the wind as the camera pushes in and slows to slow motion.
  He stays facing right.

SHOT 17 (19.2–20.2s) — Fashion reveal montage (three rapid inserts, ~0.33s each)
  a) Polished black lace-up boots planting in the sand.
  b) Silver rings and layered chains catching the sunlight.
  c) Slim black sunglasses sliding into place over his eyes.

[ACT 4 — THE DEFEAT: the punchline]

SHOT 18 (20.2–21.7s) — Medium close-up: the man realizes
  Profile, facing right. He looks down at himself, lifts the leather lapel with his left
  hand, and his face melts from shock into humbled awe. He murmurs in Japanese:
  「カッコ良すぎる...」

SHOT 19 (21.7–22.9s) — Wide side-on master: he falls
  Wide side-on shot of both of them. He tips stiffly forward and falls face-first into the soft
  sand like a toppled plank — a comedic, theatrical faint, completely unhurt. A puff of sand
  rises, his coat flutters down over him. The grandmother stands tall on the right.

SHOT 20 (22.9–24.0s) — Final hero shot: the grandmother (the ONLY look to camera)
  Medium close-up. She turns her face to the camera, raises the revolver near her lips and
  gently blows the thin curl of smoke from the muzzle, then gives a small, cool wink.
  The fallen man lies blurred in the background on the left. Freeze frame on the wink.

SOUND DESIGN
- Tense spaghetti-western whistle and twangy guitar under Act 1, wind and ticking silence.
- Gunshots: sharp, cinematic cracks with echo across the desert.
- Bullet cams: slowed-down whoosh with a deep bass hum.
- Transformations: a satisfying fabric swoosh plus a sparkling shimmer.
- Fall: soft comedic thud into sand. Final wink: a single playful guitar sting.
```
