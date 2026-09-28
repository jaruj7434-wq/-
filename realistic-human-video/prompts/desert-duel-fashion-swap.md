# Desert Duel — Fashion Swap(Blender モーション用プロンプト)

- 尺: 約20秒 / 24fps(480フレーム)/ 14カット
- 解像度: 1080×1920(9:16 縦型)
- 用途: Higgs Field でのモーショントランスファー用の参照動画(素体は後でリアルな人物に置き換える)
- ファッション要素: 被弾のたびに全身コーデが切り替わる(衣装そのものは Higgs Field 側で生成。Blender では切り替えタイミングと「見せるカメラワーク」を作る)

## Prompt (English)

```
Create a cinematic Blender animation to be used as a motion reference for AI motion transfer.
It is a Western-style duel told with many camera cuts and camera moves.

FORMAT
- Vertical 9:16, 1080x1920, 24 fps, 20 seconds (frames 1–480), 14 shots.
- Two rigged, neutral grey mannequin characters (realistic adult male proportions, ~180 cm tall)
  with a face rig or shape keys for the jaw, lips and eyes (needed for the mouth close-ups).
  Simple placeholder cowboy hats and revolvers (with animatable hammer and trigger).
  No detailed clothing — the outfits will be replaced later by AI.
- Light grey bodies against a warm sand-colored ground and a pale sky gradient so every pose
  reads clearly.

SET
- Flat desert ground with low dunes, scattered rocks, and a few dry tumbleweeds.
- Low, warm late-afternoon sun from the side, long soft shadows, light drifting sand particles.
- The two men stand facing each other about 4 meters apart:
  LEFT MAN on the left side of the master shot, RIGHT MAN on the right side.

CAMERA SETUP
- Create one camera per shot (CAM_01 … CAM_14) and switch between them with timeline markers
  bound to cameras (Ctrl+B), so the whole edit plays in one timeline.
- Use smooth Bezier easing on all camera moves; add very subtle handheld noise
  (Noise modifier, small strength) only where noted.
- Use depth of field with animated focus distance for the rack-focus shots.

SHOT LIST

SHOT 01 — Frames 1–48 (2.0s) — Establishing crane down
  CAM_01 starts high in the sky looking down at the desert and cranes down and forward,
  ending on a side-on wide shot at chest height with both men fully in frame, guns aimed at
  each other. A tumbleweed rolls between them.
  Action: both men hold aim, slight breathing, small weight shifts.

SHOT 02 — Frames 49–72 (1.0s) — Extreme close-up: left man's eyes
  CAM_02: extreme close-up of the LEFT MAN's eyes under the hat brim, slow push-in.
  Action: eyes narrow, a slow blink.

SHOT 03 — Frames 73–96 (1.0s) — Extreme close-up: right man's gun hand
  CAM_03: macro shot of the RIGHT MAN's hand on the revolver grip. Rack focus from the hand to
  the cylinder.
  Action: fingers tighten on the grip, thumb pulls back the hammer (click).

SHOT 04 — Frames 97–144 (2.0s) — Close-up: left man's mouth (dialogue)
  CAM_04: low-angle close-up of the LEFT MAN's lower face (mouth, jaw, chin, hat brim edge),
  very slow push-in.
  Action: he says one short line. Animate clear, natural lip sync shapes: lips part,
  jaw opens and closes 5–6 times, corner of the mouth curls into a slight smirk at the end.

SHOT 05 — Frames 145–156 (0.5s) — Over-the-shoulder: left man fires
  CAM_05: over the RIGHT MAN's shoulder (his shoulder blurred in the foreground), framing the
  LEFT MAN in medium shot.
  Action: the LEFT MAN pulls the trigger — sharp recoil (wrist and forearm kick up ~15°,
  shoulder jolts back). Bright muzzle flash (emissive sphere, 2 frames) and a small smoke puff.
  Short camera shake (3 frames) on the shot.

SHOT 06 — Frames 157–192 (1.5s) — Bullet cam (slow motion)
  CAM_06 flies alongside the bullet in extreme slow motion. The bullet (small glowing brass
  object) spins on its axis and leaves a faint heat-distortion trail through drifting sand
  particles. The camera slowly orbits 90° around the bullet while tracking it.
  In the last 8 frames the RIGHT MAN's chest fills the background as the bullet reaches him.

SHOT 07 — Frames 193–240 (2.0s) — Right man hit + fashion reveal orbit
  CAM_07: full-body shot of the RIGHT MAN.
  Action: the bullet hits his chest (frame 194); his upper body jerks back, arms flinch.
  OUTFIT CHANGE MARKER: at frame 196 a bright white flash covers his whole body for 4 frames.
  After the flash, the camera performs a fast-to-slow 180° orbit around him (ease-out) while he
  straightens up, so his new outfit is shown from front, side and back.
  He glances down at himself, then looks up.

SHOT 08 — Frames 241–264 (1.0s) — Close-up: right man's face
  CAM_08: close-up of the RIGHT MAN's face, slow push-in.
  Action: jaw tightens, a small exhale through the mouth, eyes lock on target, he re-aims.

SHOT 09 — Frames 265–276 (0.5s) — Extreme close-up: right man's trigger
  CAM_09: macro shot of the RIGHT MAN's trigger finger.
  Action: finger squeezes the trigger, the hammer drops, muzzle flash and smoke at the edge of
  frame. Camera shake (3 frames).

SHOT 10 — Frames 277–300 (1.0s) — Bullet cam (reverse direction, faster)
  CAM_10 tracks behind the second bullet, faster than shot 06, with a quick rotation.
  The bullet rushes toward the LEFT MAN's chest; a sharp push-in on the final frames.

SHOT 11 — Frames 301–336 (1.5s) — Left man hit + tilt-up fashion reveal
  CAM_11: low-angle full-body shot of the LEFT MAN.
  Action: the bullet hits his chest (frame 301); upper body jerks back, gun arm drops.
  OUTFIT CHANGE MARKER: at frame 302 the same full-body white flash for 4 frames.
  After the flash, the camera tilts and cranes up from his boots to his hat, revealing the
  full new outfit.

SHOT 12 — Frames 337–372 (1.5s) — Outfit check: torso
  CAM_12: medium shot of the LEFT MAN, camera slowly orbits 45° around him.
  Action: he lowers the revolver to his side and slowly looks down at his chest and torso,
  touching the front of his outfit with his free hand.

SHOT 13 — Frames 373–408 (1.5s) — Outfit check: sleeve and boots (two inserts)
  CAM_13A (frames 373–390): close-up of his forearm — he raises his hand and slowly turns his
  wrist, looking at the sleeve and cuff. Slow slide from left to right.
  CAM_13B (frames 391–408): low shot at ground level of his boots — he shifts weight onto one
  leg and turns one boot slightly. Slow push-in.

SHOT 14 — Frames 409–480 (3.0s) — Fall and ending
  CAM_14A (frames 409–456): return to the master side-on wide shot (same framing as the end of
  shot 01).
  Action: the LEFT MAN looks up with a stunned, blank expression, his knees buckle and he falls
  stiffly forward face-down onto the sand; the revolver drops from his hand. Sand puff at
  impact (particle burst) and a 4-frame camera shake.
  CAM_14B (frames 457–480): ground-level shot with the LEFT MAN's hat and sand in the blurred
  foreground; rack focus to the RIGHT MAN in the background as he slowly lowers his gun and
  blows smoke from the muzzle. Hold on the final frame.

ANIMATION NOTES
- Natural, weighted human motion with ease-in/ease-out; no robotic linear interpolation.
- Keep the characters' body motion continuous across cuts (same animation, only the camera
  changes) so the action matches from shot to shot.
- Avoid limbs crossing in front of the torso or overlapping between the two characters.
- Leave a short pause (4–8 frames) after each outfit change marker so the new outfit can be
  shown clearly.
- In full-body shots keep the character entirely in frame (head to feet).

RENDER
- Eevee, soft lighting, no motion blur (except a light blur on the bullet shots is OK).
- Output 1: the full edited sequence as one MP4 (H.264), 1080x1920, 24 fps.
- Output 2: each shot rendered as a separate MP4 named SHOT_01.mp4 … SHOT_14.mp4
  (for per-shot AI motion transfer).
```

## メモ

- 衣装の切り替え(Before / After)は Higgs Field 側でキービジュアルを作って指定する。
- 左の男性のセリフ内容は後で決める(音声は `generate_audio` 等で別途作成。実行前に許可を取る)。
- 銃弾カット(SHOT 06 / 10)は人物が映らないため、モーショントランスファーではなく
  画像→動画生成や Blender の映像をそのまま活かす方法も検討する。
