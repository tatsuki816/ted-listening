#!/usr/bin/env python3
"""字幕の時刻と実際の音声がずれていないかを測る。

  ~/音声入力/.venv/bin/python3 ズレ検査.py treasure
  ~/音声入力/.venv/bin/python3 ズレ検査.py urban
  ~/音声入力/.venv/bin/python3 ズレ検査.py treasure --直す   # 字幕が遅れている文の開始を前へ寄せて書き込む

公開している区間の音声（audio/...）をそのまま whisper にかけ直し、各文の最初の語が鳴り始めた時刻と、
字幕データの文の開始（＋文頭の余白 0.12秒）を比べる。全体の音声で合わせた時刻を区間に切ったときに、
切り位置や mp3 の頭の無音でずれていないかを見るためのもの。
2026-10-24：本人の「音声と字幕のズレがないように」を受けて作った。トークを足したら必ず通す。

--直す は、字幕の開始が音より 0.3秒以上遅れている文だけ、開始を「聞こえた時刻−余白」まで前へ寄せる。
前の文の終わりより前には基本寄せない（よくある語が別の場所に当たったときの誤りを防ぐ）。
ただし前の文と接していて食い込みが1秒以内なら、前の文の終わりも一緒に寄せて境目を動かす。
音より早く出ている文は直さない（少し早く出る分には聞き逃さないので）。
直したら かたまり.py → 組み立て.py を回す。
"""
import json
import re
import statistics
import sys
from difflib import SequenceMatcher
from pathlib import Path

import mlx_whisper

根 = Path(__file__).parent
モデル = "mlx-community/whisper-large-v3-turbo"
設定 = {
    "urban": (Path.home() / "Documents/obsidian/法政大学2年/英語ライティング/リスニング/データ", "audio/{n}.mp3", 5),
    "treasure": (根 / "トーク/treasure/データ", "audio/treasure/{n}.mp3", 6),
}
文頭の余白 = 0.12


def 語に割る(s):
    s = s.lower().replace("’", "'").replace("—", " ").replace("–", " ").replace("--", " ")
    return re.findall(r"[a-z0-9']+", s)


名 = sys.argv[1]
直す = "--直す" in sys.argv
直した数 = 0
データ, 音声, 数 = 設定[名]
全ずれ = []
for n in range(1, 数 + 1):
    文 = json.loads((データ / f"区間{n}.json").read_text())
    r = mlx_whisper.transcribe(str(根 / 音声.format(n=n)), path_or_hf_repo=モデル, language="en",
                               word_timestamps=True, condition_on_previous_text=False)
    聞 = [(t, w["start"]) for seg in r["segments"] for w in seg.get("words", []) for t in 語に割る(w["word"])]
    正 = [(t, i, j) for i, s in enumerate(文) for j, t in enumerate(語に割る(s["text"]))]
    sm = SequenceMatcher(None, [a for a, _, _ in 正], [a for a, _ in 聞], autojunk=False)
    頭 = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                _, i, j = 正[i1 + k]
                if j == 0:
                    頭[i] = 聞[j1 + k][1]
    ずれ = [(i, 頭[i] - (文[i]["start"] + 文頭の余白)) for i in 頭]
    d = [x for _, x in ずれ]
    全ずれ += d
    大 = [(i + 1, round(x, 2)) for i, x in ずれ if abs(x) > 0.3]
    if 直す:
        変 = False
        for i, x in ずれ:
            if x < -0.3:
                新 = round(文[i]["start"] + x, 2)
                下限 = 文[i - 1]["end"] if i > 0 else 0.0
                if 新 >= 下限 - 0.05:
                    文[i]["start"] = max(新, 下限)
                    変 = True
                    直した数 += 1
                elif i > 0 and 新 >= 文[i - 1]["start"] + 0.5 and 下限 - 新 <= 1.0:
                    # 前の文と接していて、前の文の終わり（語尾の余白）が今の文の頭に食い込んでいた。境目を前へ寄せる
                    文[i - 1]["end"] = 新
                    文[i]["start"] = 新
                    変 = True
                    直した数 += 1
        if 変:
            (データ / f"区間{n}.json").write_text(json.dumps(文, ensure_ascii=False, indent=0 if 名 != "urban" else 1))
    print(f"区間{n}: 測れた文 {len(d)}/{len(文)}  ずれの中央値 {statistics.median(d):+.2f}秒  "
          f"最大 {max(d, key=abs):+.2f}秒  0.3秒を超える文 {大 or 'なし'}")
print(f"全体：中央値 {statistics.median(全ずれ):+.2f}秒  0.3秒以内 {sum(abs(x) <= 0.3 for x in 全ずれ)}/{len(全ずれ)}文")
if 直す:
    print(f"開始を前へ寄せた文：{直した数}")
