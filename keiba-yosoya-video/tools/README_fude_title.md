# 筆文字タイトル(背景透明)の作り方

S5 の最後の止め絵に重ねる「競馬予想屋 谷上さん」の筆文字アニメーション。Higgs Field は使わない(クレジット消費なし)。

1. フォントを取得(Yuji Syuku・SIL Open Font License、商用利用可)
   `curl -LO https://raw.githubusercontent.com/google/fonts/main/ofl/yujisyuku/YujiSyuku-Regular.ttf`
2. PNG連番を書き出す:`python3 tools/fude_title.py YujiSyuku-Regular.ttf frames_ink ink`(白文字は `white`)
3. 透明動画にする
   - MOV(Premiere / Final Cut / DaVinci 向け):`ffmpeg -framerate 30 -i frames_ink/f_%04d.png -c:v qtrle -pix_fmt argb fude_title_ink.mov`
   - WebM(軽量):`ffmpeg -framerate 30 -i frames_ink/f_%04d.png -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 2M -auto-alt-ref 0 fude_title_ink.webm`

- 1080x1920・30fps・4.2秒。最後の数フレームは止まった状態なので、編集で最後のフレームを伸ばせば止め絵に合わせられる。
- 配置:右列に「競馬予想屋」、左列に大きく「谷上」+「さん」。フォントを太らせ、縁のにじみ・かすれ・墨の濃淡を加えて筆書きの質感にしている。「上」の最後の画から墨の飛沫。
- ink:墨(黒)+暗い背景でも読めるうっすら白いにじみ/white:白文字。
- 出力先は `assets/output/title/`(git 管理外)。
