# TEDリスニング再生

Tim Urban の TED トーク「Inside the Mind of a Master Procrastinator」を、1文ずつ字幕つきで繰り返し聴くためのページ。
tatsuki の英語リスニング練習用（法政大学2年・2026秋）。

**https://tatsuki816.github.io/ted-listening/**

## できること

- 文をタップするとそこから再生。今の文が蛍光ペンで光る
- 繰り返し：流す／1文／A–B（範囲）／区間まるごと
- 字幕：なし（英文をぼかす）／英／日／英日。「今の文を見る」で1文だけ開ける
- 速さ 0.7／0.85／1倍、繰り返しの間 なし／1.5秒／3秒
- **1回開けば圏外でも動く**（Service Worker が5区間ぶんの音声を貯める。右上に「圏外OK」が出たら完了）
- iPhone は Safari の共有 → ホーム画面に追加 でアプリのように使える

## 構成

| ファイル | 役割 |
|---|---|
| `雛形.html` | ページの本体。`__DATA__` に字幕が入る |
| `訳.py` | 132文の日本語訳 |
| `組み立て.py` | 雛形に字幕を流し込んで `index.html` を作る |
| `sw.js` | 圏外対応。音声は Range 要求に 206 で返す（Safari の `<audio>` はこれが無いと再生できない） |
| `audio/1〜5.mp3` | 区間ごとの音声 |

字幕の時刻と英文は Obsidian の vault の `法政大学2年/英語ライティング/リスニング/データ/` から読む（書き取りツール `書き取り.py` と同じデータ）。

## 直すとき

1. `雛形.html` か `訳.py` を直す
2. `python3 組み立て.py`
3. 中身を変えたら `sw.js` と `雛形.html` の `キャッシュ名` の `v1` を上げる（上げないと古い版がスマホに残る）
4. commit して push。GitHub Pages が1分ほどで反映する

push は個人アカウント `tatsuki816` の HTTPS で行う（この Mac の ssh 鍵は別アカウントで名乗るため）。

## 出典とライセンス

音声と英文字幕：Tim Urban, "Inside the Mind of a Master Procrastinator", TED 2016。
<https://www.ted.com/talks/tim_urban_inside_the_mind_of_a_master_procrastinator>
TED Talks は CC BY-NC-ND 4.0。個人の学習用に非営利で置いている。日本語訳は学習用に独自に付けたもの。

現役（2026-09〜）。
