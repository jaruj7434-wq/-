# 故障したオールテレーンクレーンを犬たちが引っ張る(オリジナル企画)

## コンセプト
- 元動画なし。オリジナルの「オチ系」ショート動画
- フック: 急な勾配の土の凸凹坂道で、大型オールテレーンクレーンが故障して太いワイヤーで引っ張られている(何が引いているかは見せない)
- オチ: カメラがクレーン前方へ回り込むと、たくさんの犬たちが引っ張っていた

## 構成案(15秒)
| 秒 | 映像 | カメラ |
|---|---|---|
| 0–5 | 急な土の坂道を、黄色い大型オールテレーンクレーンがハザードを点滅させながらゆっくり登る。エンジン付近から薄い煙。ブームの先端から太い鋼鉄ワイヤーがピンと張って坂の上へ伸びる。ワイヤーの先は画面外 | 坂の下・クレーン後方からのローアングル。ワイヤーを追ってゆっくりティルトアップ |
| 5–9 | クレーンの横を通って前方へ移動。ワイヤーが坂の上へ続いている。まだ引いているものは見えない | クレーン横を進むドリー/ドローン風 |
| 9–15 | オチ: ワイヤーの先にはハーネスを着けた何匹もの犬たち(犬ぞりのように2列)が、全力で坂を登りながら引っ張っている。カメラは犬たちの正面に回り込み、得意げな顔のアップで終わる | 犬たちの前方へ回り込み、正面から |

## 推奨モデル・設定
- `seedance_2_5` / t2v(文字だけ)/ 15秒 / 9:16 / 音声あり
- 480p: 45 クレジット / 720p: 105 クレジット(無制限枠は対象外)

## プロンプト(案)
```
Photorealistic vertical video, one continuous 15-second shot, cinematic but natural documentary look, overcast daylight.

0-5s: Low angle from behind and below a huge yellow all-terrain mobile crane with many wheels, crawling slowly up a very steep, rough, rutted dirt hill road with rocks and muddy bumps. The crane has clearly broken down: hazard lights blinking, a thin wisp of smoke from the engine, the boom retracted. A thick steel tow cable is attached to the front of the crane and stretches tight up the slope, out of frame. We cannot see what is pulling it. Camera slowly tilts up along the taut cable.

5-9s: The camera glides forward along the side of the crane, passing the giant tires that slowly turn and slip in the dirt, following the tense cable further up the hill. Still nothing visible at the end of the cable, building suspense.

9-15s: Reveal: the camera swings around to the front and finds the cable is hitched to a large team of about twenty dogs in pulling harnesses, arranged in pairs like a sled-dog team: huskies, malamutes, golden retrievers, shiba inus, corgis and French bulldogs, all pulling with full effort up the steep hill, paws digging into the dirt, tongues out, tails up. The camera ends in front of the team, a slight low angle on the lead dogs' proud determined faces as the crane follows behind them.

Realistic physics, dust and small stones kicked up, crane engine rumble, creaking cable, dogs panting and barking.
```

## 生成 #1(2026-10-27)
- 上記プロンプトそのまま / seedance_2_5 t2v / 15秒 / 9:16 / 480p / 音声あり / 45 クレジット
- 犬種ミックス・約20匹・曇り
- job_id: `827ccb72-8ad3-4390-8446-04e638a3cfcf`
- 結果: **NG**。ブームのないクレーンになり、下り坂に見えた(原因: "boom retracted" と書いたこと、坂とカメラの向きを書かなかったこと)

## プロンプト v2(台本 v2・絵コンテ v2 に対応、未生成)
```
Photorealistic vertical 9:16 video, one continuous 15-second shot, natural documentary look, overcast daylight.

FIXED RULES FOR THE WHOLE VIDEO:
- The road is a very steep UPHILL dirt road, rough and rutted with rocks and bumps. Screen-left is the bottom of the hill, screen-right is the top of the hill. Everything moves UP the hill, to the right.
- The vehicle is a large yellow all-terrain mobile crane with five axles of big tires and a long, thick, clearly visible telescopic crane boom lying on top of the carrier, extending forward past the driver's cab with a hook block at its tip. The boom must be visible in every shot of the crane.
- The crane has broken down on the climb: orange hazard lights blinking, a thin wisp of smoke from the engine, wheels slipping. It cannot climb by itself.
- A thick steel tow cable runs from the crane's front tow hook straight UP the hill, pulled tight.
- About twenty dogs in pulling harnesses (huskies, malamutes, golden retrievers, shiba inus, corgis, French bulldogs), in two rows like a sled-dog team, are ABOVE the crane on the hill and pull the cable UPHILL.

0-4s: Side view from slightly below. The whole crane fills the frame, tilted up to the right on the steep slope, boom on top, hazard lights, smoke. The tight cable goes up to the right and leaves the frame. No dogs visible yet. Camera nearly still, slowly moving right (uphill).
4-8s: Camera tracks uphill alongside the crane: close-up of the huge tires slipping on the bumpy dirt and kicking up soil, the underside of the boom overhead. The crane creeps upward, pulled by the cable.
8-11s: Camera passes the driver's cab and the boom tip and follows the tense cable up the slope. The cable disappears over a small crest; we still cannot see what is pulling.
11-15s: Reveal. Camera is now uphill in front of the dog team, looking down the slope: in the foreground the lead dogs' faces, behind them two rows of dogs climbing toward the camera with full effort, paws digging into the dirt, tongues out; far behind them, lower on the hill, the yellow crane with its boom attached to the cable. The camera slowly backs up the hill and ends close on the proud, determined face of the lead dog.

Sound: struggling crane engine, creaking steel cable, tires scraping dirt, then dogs panting and barking happily.
```
