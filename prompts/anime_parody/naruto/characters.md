# ナルト風 実写化パロディ — キャラクター設定

## 主人公(ナルト風の忍者青年)

- 幼少期版: 12歳くらいの架空の日本人の男の子(実在の俳優・子役には似せない)※v2以降の基準
- 青年版: 18歳くらい(v1)
- ツンツンの明るい金髪、両頬に3本ずつのヒゲ風フェイスペイント
- 少し着古したオレンジと黒のジャージ風の忍者服
- 紺色の布の額当て。紋章は「箸入りラーメンどんぶり」(公式の木の葉マーク・渦巻きは使わない)
  - 渦巻きと指定すると公式マークに寄ってしまうため、v2 からどんぶりに変更

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| v1 | gpt_image_2_6 | 9:16 | 0.75 クレジット | 312e5960-df37-4432-b1ad-e28746af33f6 | 雰囲気は良い。ただし額当ての紋章が公式マークに近く、ヒゲ線が片頬にしか出ていない → 要修正 |
| v2(幼少期・全身正面) | gpt_image_2_6 | 9:16 | 0.75 クレジット | 7e8b0bb0-7236-4eb8-ac01-cacea04fb696 | 全身・正面・グレー背景。両頬にヒゲ線、ラーメン紋章もOK。紋章がラーメンなので差し替え |
| v3(v2の紋章のみ編集) | gpt_image_2_6(v2参照) | 9:16 | 0.75 クレジット | 957dcbb8-d016-4d5c-97ba-f4057545d575 | 顔・服・ポーズはv2を維持。紋章がカナダ国旗風のもみじになった → 葉の形を再検討中 |

#### v1 プロンプト

```
Photorealistic live-action film still, vertical 9:16. A fictional Japanese young man around 18, original face (not resembling any real actor), spiky messy bright blond hair, three faint thin whisker-like face-paint lines on each cheek, wearing a slightly worn bright orange and black zip-up tracksuit-style ninja outfit, a dark blue cloth forehead protector with a small metal plate engraved with an original spiral-swirl emblem. Confident grin, thumb pointing at himself. Standing on an ordinary Japanese suburban street in the morning, cinematic natural lighting, shallow depth of field, 35mm film look, realistic skin texture. No text, no logos.
```

#### v2 プロンプト(幼少期・全身正面)

```
Photorealistic live-action character reference photo, vertical 9:16, full body shot from head to shoes, subject standing straight and facing the camera directly (front view), arms relaxed at sides, centered in frame. A fictional Japanese boy around 12 years old, original face (not resembling any real actor), spiky messy bright blond hair, exactly three thin whisker-like face-paint lines drawn on BOTH cheeks (left and right, symmetrical). Wearing a slightly oversized bright orange and black zip-up tracksuit-style ninja outfit with matching orange pants, dark blue sandals-style shoes. Dark blue cloth headband with a small plain metal plate engraved with a simple cartoon ramen bowl emblem (a bowl with chopsticks), clearly a ramen bowl, no leaf shape, no spiral. Mischievous confident grin. Plain light gray seamless studio background, soft even studio lighting, sharp focus, realistic skin and fabric texture. No text, no logos.
```

#### v3 プロンプト(v2 を参照画像にして紋章のみ編集)

```
Edit this exact photo. Keep everything identical: the same boy, same face, same expression, same blond hair, same whisker lines on both cheeks, same orange and black outfit, same pants, pouch and leg band, same sandals, same front-facing full-body pose, same plain light gray studio background, same lighting and framing. Change ONLY the engraving on the metal plate of the dark blue headband: remove the ramen bowl and replace it with a simple engraved outline of a single plain maple-style leaf with pointed lobes and a short stem, drawn as clean engraved lines. The leaf must NOT contain any spiral or swirl and must not be a rounded teardrop leaf shape. No text, no logos.
```

- メモ: "maple-style leaf" と指定するとカナダ国旗のもみじになりやすい。
