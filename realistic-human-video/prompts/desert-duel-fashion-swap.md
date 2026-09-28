# Desert Duel — Fashion Swap(Blender モーション用プロンプト)

- 尺: 約15秒 / 24fps(360フレーム)
- 解像度: 1080×1920(9:16 縦型)
- 用途: Higgs Field でのモーショントランスファー用の参照動画(素体は後でリアルな人物に置き換える)
- ファッション要素: 被弾のたびに全身コーデが切り替わる(衣装そのものは Higgs Field 側で生成。Blender では切り替えタイミングのみ示す)

## Prompt (English)

```
Create a Blender animation to be used as a motion reference for AI motion transfer.

FORMAT
- Vertical 9:16, 1080x1920, 24 fps, ~15 seconds (frames 1–360).
- Two rigged, neutral grey mannequin characters (realistic adult male proportions, ~180 cm tall).
  Simple placeholder cowboy hats on both. No detailed faces or clothing — the outfits will be
  replaced later by AI.
- Solid, high-contrast silhouettes: light grey bodies against a warm sand-colored ground and a
  pale sky gradient, so the poses read clearly.
- Both bodies must stay fully in frame (head to feet) for the whole animation.

SET
- Flat desert ground with a few low dunes and scattered rocks in the background.
- Low, warm late-afternoon sun from the side, long soft shadows.
- The two men stand facing each other, about 4 meters apart, in profile to the camera:
  LEFT MAN on the left side of frame, RIGHT MAN on the right side.

CAMERA
- Static side-on wide shot at chest height, framing both men head to toe.
- Optional: a subtle slow push-in (5%) during the final beat (frames 250–360).

ACTION TIMELINE
1. Frames 1–48 — Standoff
   Both men stand with feet shoulder-width apart, arms extended, each gripping a revolver with
   one hand, muzzles pointed at each other's chest. Slight breathing motion, a small weight
   shift. Tension, no big movement.

2. Frames 49–84 — Left man speaks
   The LEFT MAN tilts his head slightly and moves his jaw as if saying one short line
   (about 1.5 seconds). The gun stays aimed.

3. Frames 85–96 — Left man fires
   The LEFT MAN pulls the trigger: a sharp recoil — wrist and forearm kick up ~15°, shoulder
   jolts back, then returns to aim.
   Add a small bright muzzle flash (emissive sphere, 2 frames) and a tiny glowing bullet
   object that travels in a straight line to the RIGHT MAN's chest in 4 frames.

4. Frames 97–120 — Hit on the right man + outfit change marker
   The bullet hits the RIGHT MAN's chest. His upper body jerks back slightly, arms flinch,
   then he recovers his stance without falling.
   OUTFIT CHANGE MARKER: at frame 98, a bright white burst/flash covers the RIGHT MAN's whole
   body for 4 frames (a white emissive shell or flash plane). This marks the moment his
   full-body outfit changes.
   He briefly glances down at himself (head tilts down, ~12 frames), then looks back up and
   re-aims at the LEFT MAN.

5. Frames 121–150 — Right man fires
   The RIGHT MAN pulls the trigger with the same recoil motion, muzzle flash, and a bullet that
   travels to the LEFT MAN's chest in 4 frames.

6. Frames 151–170 — Hit on the left man + outfit change marker
   The bullet hits the LEFT MAN's chest. His upper body jerks back and his gun arm drops
   slightly.
   OUTFIT CHANGE MARKER: at frame 152, the same full-body white flash on the LEFT MAN for
   4 frames.

7. Frames 171–290 — Left man slowly checks his outfit
   The LEFT MAN lowers the revolver to his side. Slowly and deliberately:
   - looks down at his chest and torso,
   - raises his free hand and looks at his sleeve and wrist, turning the forearm,
   - glances down to his legs and boots, shifting weight onto one leg,
   - looks back up with a stunned, blank posture.
   Keep these moves slow and readable (like a fashion "outfit check").
   The RIGHT MAN holds his aim, completely still.

8. Frames 291–340 — Left man falls forward
   The LEFT MAN's knees buckle, his body tips forward stiffly, and he falls face-down onto the
   sand. The revolver drops from his hand. Add a small puff of sand at impact (simple particle
   burst).

9. Frames 341–360 — Hold
   The LEFT MAN lies still on the ground. The RIGHT MAN slowly lowers his gun. End on a held
   frame.

ANIMATION NOTES
- Use natural, weighted human motion with ease-in/ease-out; avoid robotic linear interpolation.
- Avoid limbs crossing in front of the torso or overlapping between the two characters.
- Keep motions moderate in speed (except recoil and hit reactions) so AI motion transfer can
  track them cleanly.
- Leave a short pause (4–8 frames) after each outfit change marker so the new outfit can be
  shown clearly.
- Render with Eevee, flat/soft lighting, no motion blur, output as MP4 (H.264).
```

## メモ

- 衣装の切り替え(Before / After)は Higgs Field 側でキービジュアルを作って指定する。
- 左の男性のセリフ内容は後で決める(音声は `generate_audio` 等で別途作成。実行前に許可を取る)。
