#!/usr/bin/env python3
"""雛形.html に字幕データを流し込んで index.html を作る。

  python3 組み立て.py

字幕の時刻と英文は Obsidian の vault（書き取りツールと同じデータ）から読む。
日本語訳は 訳.py。どちらかを直したらこれを回して push する。
"""
import json
from pathlib import Path

import 訳

根 = Path(__file__).parent
元 = Path.home() / "Documents/obsidian/法政大学2年/英語ライティング/リスニング/データ"
見出し = {1: "レポートの先延ばし", 2: "脳の中のサル", 3: "パニック・モンスター",
          4: "TEDの準備", 5: "締切の無い先延ばし"}

DATA = {}
for i in range(1, 6):
    文 = json.loads((元 / f"区間{i}.json").read_text())
    ja = 訳.訳[i]
    if len(文) != len(ja):
        raise SystemExit(f"区間{i}: 英文 {len(文)} 件に対して訳が {len(ja)} 件。訳.py を揃える")
    DATA[str(i)] = {"見出し": 見出し[i],
                    "文": [{"s": round(s["start"], 2), "e": round(s["end"], 2),
                            "en": s["text"].strip(), "ja": ja[n]} for n, s in enumerate(文)]}

雛形 = (根 / "雛形.html").read_text()
if "__DATA__" not in 雛形:
    raise SystemExit("雛形.html に __DATA__ が無い")
(根 / "index.html").write_text(雛形.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)))
print(f"index.html を作った（{sum(len(v['文']) for v in DATA.values())} 文）")
