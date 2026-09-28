# Desert Duel — シーン構築(モデル配置のみ)

`desert-duel-fashion-swap.md` のアニメーションを付ける前段階として、
人物・小道具・背景・ライト・メインカメラの **配置だけ** を作るプロンプト。
アニメーション(キーフレーム)は含めない。

## Prompt (English)

```
Build a static Blender scene (models and layout only, NO animation / NO keyframes).
This scene will later be animated as a motion reference for AI motion transfer.

GENERAL
- Units: metric, 1 unit = 1 meter. Z is up. Frame rate 24 fps, frame range 1–480
  (set it now, but do not animate anything).
- Render resolution 1080x1920 (vertical 9:16), render engine Eevee.
- Organize objects into collections: CHARACTERS, PROPS, ENVIRONMENT, LIGHTS, CAMERAS.
- Give every object a clear name as listed below.

CHARACTERS (collection: CHARACTERS)
Create two identical but separate humanoid mannequins:
- Names: MAN_LEFT and MAN_RIGHT (meshes), RIG_LEFT and RIG_RIGHT (armatures).
- Realistic adult male proportions, height 1.80 m, athletic build.
- Smooth, neutral light-grey matte material (no clothing, no detailed face texture).
  Give MAN_LEFT a slightly warmer grey and MAN_RIGHT a slightly cooler grey so they are
  easy to tell apart.
- Full humanoid armature (e.g. Rigify human metarig, generated and bound with automatic
  weights), including:
  - spine, neck, head,
  - full arms with individual finger bones (index finger must be able to pull a trigger),
  - legs and feet with IK controls,
  - a face setup for the mouth close-ups: jaw bone plus shape keys for
    mouth open, lips part, smile/smirk (left and right corners), blink (both eyes),
    eye squint.
- Simple eyes (spheres) so eye direction reads in close-ups.
- Rest pose: T-pose. Then set a STATIC standoff pose (pose mode only, no keyframes):
  feet shoulder-width apart, knees slightly bent, right arm extended forward at shoulder
  height holding the revolver, left arm relaxed at the side, head facing the opponent.

PROPS (collection: PROPS)
- HAT_LEFT, HAT_RIGHT: simple placeholder cowboy hats (low-poly, medium grey), parented to
  each character's head bone.
- REVOLVER_LEFT, REVOLVER_RIGHT: simple six-shot revolvers (~30 cm long, dark grey metal),
  parented to each character's right hand bone, grip in the palm, index finger on the
  trigger. Separate child objects for HAMMER, TRIGGER and CYLINDER so they can be animated
  later (set their origins at the pivot points).
- BULLET_01, BULLET_02: small brass bullets (~1 cm diameter, 2 cm long) with a glowing
  emissive material, hidden in viewport and render for now, placed at each gun muzzle.
- MUZZLE_FLASH_LEFT, MUZZLE_FLASH_RIGHT: small emissive spheres at each muzzle, hidden for now.
- OUTFIT_FLASH_LEFT, OUTFIT_FLASH_RIGHT: white emissive shells slightly larger than each body
  (e.g. a duplicated body mesh with a Displace/Solidify offset), hidden for now.
- TUMBLEWEED: one low-poly tumbleweed placed on the ground off-screen to the left.

PLACEMENT
- MAN_LEFT at location (-2.0, 0, 0), facing +X (toward MAN_RIGHT).
- MAN_RIGHT at location (2.0, 0, 0), facing -X (toward MAN_LEFT).
- The two men are 4 meters apart, both muzzles aimed at each other's chest height (~1.35 m).

ENVIRONMENT (collection: ENVIRONMENT)
- GROUND: large plane (200 x 200 m) with subtle sand displacement (noise texture), warm
  sand-colored material with fine grain.
- DUNES: a few low, smooth dunes in the background (Y = +20 to +60 m), 2–6 m high.
- ROCKS: 5–8 scattered low-poly rocks at various distances, none between the two men.
- SKY: World shader with a pale warm sky gradient (Sky Texture or a simple gradient),
  light haze/mist for depth.

LIGHTS (collection: LIGHTS)
- SUN: Sun lamp, low late-afternoon angle (~15° above the horizon), coming from the side
  (from -X / camera-left), warm color (~4500K), strength so the characters cast long soft
  shadows across the sand.
- FILL: soft area light (or world light) on the camera side to keep the grey bodies readable.

CAMERA (collection: CAMERAS)
- CAM_MASTER: side-on wide shot at chest height.
  Location (0, -9.5, 1.3), rotation facing +Y (looking at the two men), focal length 35 mm.
  Both men must be fully in frame head to feet in the 9:16 vertical frame, centered.
  Set it as the active scene camera.
- Do not create the other shot cameras yet.

OUTPUT
- Save the file as desert_duel_setup.blend.
- Render a single still from CAM_MASTER (desert_duel_setup_preview.png) so the layout can
  be checked.
```

## チェックポイント(Blender で確認すること)

- 二人が 9:16 の縦画面に頭からつま先まで収まっているか
- 銃口がお互いの胸の高さを向いているか
- 指・顎・まぶたが動くか(ポーズモードで試す)
- 銃・帽子が手と頭に追従するか(ボーンを動かして確認)
