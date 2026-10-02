# MARUKOME カート動画 v4 — 服装②(白T+金ネックレス)・慶太キャラ固定

- v3(`7e0fc637-…`)はジャケットの中がワイシャツ+ネクタイになったため作り直し。
- 構成・カメラワークは v3(`marukome-cart-v3-camera-analysis.md`)と同じ。服装指定とキャラ固定を強化。
- 参照: 1) 慶太×服装② 全身 `452bbba9-1bcc-41b1-b7ed-7aa6d9f58e95`(job 514c99e6 を取り込み直し) 2) 看板 `7ea7deb8-1528-4214-a6d2-0a4b58f1d648` 3) 慶太 element `f6c17cc9-…`
- 服装①の画像(ストライプシャツ入り)は参照から外す。
- seedance_2_5 / omni_reference / 15秒 / 9:16。費用: 480p 45 / 720p 105 / 1080p 180

## Prompt
```
A 15-second vertical (9:16) photorealistic fashion commercial short film, action-comedy, shot on
35mm film with a warm, clean, high-end look. Location: a long, perfectly straight boulevard lined
with very tall palm trees in a sunny Southern California-style city, parked cars on both sides.
Time: bright midday the whole film — clear blue sky, strong high sun, crisp highlights, vivid
natural colors.

REFERENCES: attached image 1 = the young man himself, full body, in the exact outfit for this
film (his identity and outfit master); attached image 2 = the MARUKOME billboard (use it exactly).
ONE CHARACTER ONLY — CHARACTER LOCK: the young man is <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>>,
the same person as in attached image 1. Keep his face identical to his reference and to image 1
in every single frame — same eyes, nose, mouth, jawline, skin tone, hairstyle and age — including
close-ups, profiles, fast motion and motion blur. Never beautify, reshape, morph or swap his face;
no facial distortion. No cap, no hat.
Outfit (the fashion focus, exactly as in image 1): a navy track jacket with white piping and a
half zip worn open, a plain pure-white crew-neck T-shirt underneath, a gold chain necklace over
the T-shirt, very wide dark navy cargo trousers, black leather loafers. NO dress shirt, NO
collar, NO necktie, NO striped shirt.

SHOT 1 (0.0–4.0s) — Cart-mounted front rig
Camera rigidly mounted on the front edge of a red metal shopping cart, 24mm wide lens at his chest
height, tilted slightly up, looking back at him as he sits inside the cart facing the lens. His
wide cargo trousers fill the bottom of the frame in the foreground. The cart rolls slowly down the
middle of the boulevard: he stays fixed in the frame while the palm trees and parked cars slide
past behind him toward a centered vanishing point; subtle road vibration.
0.0–1.0s: head tipped back against the cart, eyes closed, totally limp in the sun.
1.0–2.0s: he lifts his head, looks straight into the lens and mutters something, bored.
2.0–2.5s: he flings both arms out wide in a big lazy gesture.
2.5–4.0s: he hooks his arms over the sides of the cart and lets his head roll to one side,
melting back into a lazy slouch. Hard cut.

SHOT 2 (4.0–5.9s) — Locked-off road-center wide
Camera fixed in the middle of the road about one meter above the asphalt, 50mm lens, perfectly
symmetrical one-point perspective down the palm boulevard. Far away, the red shopping cart comes
racing straight toward the camera at high speed with him lying back inside, legs and loafers
sticking up over the front, jacket flapping. At 5.5s the cart's front wheels lift into a wheelie;
at 5.8s the cart blasts past just over the top-right corner of the lens as a dark blur. Hard cut.

SHOT 3 (5.9–6.9s) — Under-cart rig, approaching the ramp
Camera mounted underneath the cart's basket facing forward, ultra-wide lens: the red wire bottom
of the basket fills the top third of the frame, the two front caster wheels hang in the lower
frame, the asphalt rushes underneath with the basket's grid shadow on it. A wooden plywood jump
ramp, with a pile of scrap lumber beside it, rushes toward the lens; at 6.6s the wheels slam onto
the ramp with heavy motion blur. Hard cut.

SHOT 4 (6.9–7.5s) — Under-cart rig, airborne
Same rig: the cart is flying high in the air. The caster wheels dangle against the blue sky;
far below are the street, a traffic light and palm trees. A brief weightless moment. Hard cut.

SHOT 5 (7.5–10.0s) — Locked-off billboard wide (no cut until the end of the film)
Camera on the opposite sidewalk at head height, looking across the road at the billboard straight
on. The billboard is EXACTLY the one in attached image 2 — same wide cream panel, same
half-body photo of him, same navy "MARUKOME" lettering, same steel legs and catwalk — standing on
the roadside verge behind the sidewalk, parallel to the road, never in the road. Its text must
stay exactly "MARUKOME" (M-A-R-U-K-O-M-E) in every frame. At 8.0s the empty shopping cart flies
in from the sky and crashes onto the billboard's catwalk, where it gets stuck. From 8.5s only a
pair of wide navy cargo trousers dangles from the catwalk, swinging — nobody is inside them. The
camera holds perfectly still.

SHOT 6 (10.0–14.6s) — Same shot continues: he pops up
At 10.0s the top of his head rises into the bottom of the frame right in front of the lens. He
stands up into a medium close-up, the billboard behind him over his shoulder, completely unhurt
and fully dressed in the outfit. 10.5–11.5s: he smooths his hair with one hand and looks straight
into the lens with a huge relieved expression. 12.0–13.0s: he breathes out, mutters something,
glances down. 13.0–14.0s: he turns his head and looks back over his right shoulder at the
billboard and the dangling trousers. 14.0–14.6s: he turns back to the camera. Slight handheld
float from here on.

SHOT 7 (14.6–15.0s) — Hand covers the lens
He raises his right hand, open palm toward the camera, and covers the lens; the frame goes dark
and ends on black.

SOUND: shopping-cart wheels rattling on asphalt, wind rush, a wooden ramp thump, a big comedic
metal crash on the billboard, then a quiet relieved exhale; an upbeat music sting at the end.
No captions, no on-screen credits, no text anywhere except "MARUKOME" on the billboard.
```
