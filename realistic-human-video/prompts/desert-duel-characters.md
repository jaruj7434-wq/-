# Desert Duel — 登場人物と単体画像プロンプト

Blender は使わず、「画像生成 → 動画化」で制作する方針に変更(2026-09-30)。

## 登場人物(Soul Cinema)

| 役 | 画面位置 | 登録名 | soul_id | 最初の衣装 |
|---|---|---|---|---|
| 若いボーダーシャツの男性(先に撃つ) | 左 | Chill Nautical Vibes | `07038e56-a229-48fb-8d75-c7529cd978ae` | 登録時のまま(ボーダーシャツ) |
| 青い服のおばあさん(撃ち返す) | 右 | Graceful Cleanup Warrior | `2a7c73bb-6eb4-4777-885a-b57bf47f9989` | 登録時のまま(青い服) |

- Soul は1回の生成に1人しか使えないため、まず1人ずつ単体画像を作る。
- その後、単体画像を参照エレメントとして登録し、二人が向かい合うカットを作る。

## ステップ1: 単体画像

- モデル: `soul_cinematic`(Soul Cinema)/ quality `2k` / `9:16`
- 無制限枠: このモデルは対象外(クレジット消費)

### 男性(左・画面右向き)

```
Cinematic full-body photograph of a young man in his twenties wearing his signature
horizontal-striped Breton shirt and his usual casual outfit, standing on sunbaked desert sand
in a Western-style duel standoff. He is in three-quarter profile facing screen right, feet
shoulder-width apart, right arm extended, gripping an old silver revolver aimed toward the
right edge of the frame. Focused, tense expression, eyes slightly narrowed.
Low warm late-afternoon sun from screen left, long soft shadows on the sand, fine dust in the
air, distant dunes and scattered rocks, pale warm sky. Photorealistic, natural skin texture,
35mm film look, shallow depth of field. Entire body visible from head to shoes.
```

### おばあさん(右・画面左向き)

```
Cinematic full-body photograph of an elderly grandmother wearing her signature blue outfit,
standing on sunbaked desert sand in a Western-style duel standoff. She is in three-quarter
profile facing screen left, feet planted firmly, right arm extended, gripping an old silver
revolver aimed toward the left edge of the frame. Calm, fearless expression with a faint
knowing smile.
Low warm late-afternoon sun from screen left, long soft shadows on the sand, fine dust in the
air, distant dunes and scattered rocks, pale warm sky. Photorealistic, natural skin texture,
35mm film look, shallow depth of field. Entire body visible from head to shoes.
```
