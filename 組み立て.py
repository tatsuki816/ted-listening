#!/usr/bin/env python3
"""雛形.html に字幕データを流し込んで index.html を作る。

  python3 組み立て.py

トークは下の トーク に並べた順でボタンになる。
- urban：字幕の時刻と英文は Obsidian の vault（書き取りツールと同じデータ）、日本語訳は 訳.py
- treasure：トーク準備.py が作った トーク/treasure/データ、日本語訳は トーク/treasure/訳.py
どちらかを直したらこれを回して push する。英文を直したら かたまり.py も回し直す。
"""
import importlib.util
import json
from pathlib import Path

根 = Path(__file__).parent


def 訳を読む(p):
    spec = importlib.util.spec_from_file_location("訳", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.訳


トーク = {
    "urban": {"話者": "Tim Urban", "題": "Inside the Mind of a Master Procrastinator", "年": 2016, "wpm": 162,
              "出典": "https://www.ted.com/talks/tim_urban_inside_the_mind_of_a_master_procrastinator",
              "音声": "audio/{n}.mp3",
              "データ": Path.home() / "Documents/obsidian/法政大学2年/英語ライティング/リスニング/データ",
              "訳": 根 / "訳.py",
              "見出し": {1: "レポートの先延ばし", 2: "脳の中のサル", 3: "パニック・モンスター",
                       4: "TEDの準備", 5: "締切の無い先延ばし"}},
    "treasure": {"話者": "Julian Treasure", "題": "How to speak so that people want to listen", "年": 2013, "wpm": 171,
                 "出典": "https://www.ted.com/talks/julian_treasure_how_to_speak_so_that_people_want_to_listen",
                 "音声": "audio/treasure/{n}.mp3",
                 "データ": 根 / "トーク/treasure/データ",
                 "訳": 根 / "トーク/treasure/訳.py",
                 "見出し": {1: "はじめに・悪い癖1〜3", 2: "悪い癖4〜7", 3: "HAIL",
                          4: "声の道具：register と timbre", 5: "prosody・pace・pitch・volume",
                          6: "ウォームアップと締め"}},
}

def データを作る():
    # リピーティング用のかたまり（かたまり.py が作る）
    塊 = json.loads((根 / "かたまり.json").read_text())
    DATA = {}
    for 名, t in トーク.items():
        訳 = 訳を読む(t["訳"])
        区間 = {}
        for i in t["見出し"]:
            文 = json.loads((t["データ"] / f"区間{i}.json").read_text())
            ja = 訳[i]
            塊i = 塊[名][str(i)]
            if len(文) != len(ja):
                raise SystemExit(f"{名} 区間{i}: 英文 {len(文)} 件に対して訳が {len(ja)} 件。訳を揃える")
            if len(文) != len(塊i):
                raise SystemExit(f"{名} 区間{i}: 英文 {len(文)} 件に対してかたまりが {len(塊i)} 文分。かたまり.py を回し直す")
            for n, s in enumerate(文):
                if " ".join(c["en"] for c in 塊i[n]) != " ".join(s["text"].split()):
                    raise SystemExit(f"{名} 区間{i} {n+1}文目: かたまりをつないでも英文と一致しない。かたまり.py を回し直す")
            if not (根 / t["音声"].format(n=i)).exists():
                raise SystemExit(f"{名} 区間{i}: 音声 {t['音声'].format(n=i)} が無い")
            区間[str(i)] = {"見出し": t["見出し"][i],
                           "文": [{"s": round(s["start"], 2), "e": round(s["end"], 2),
                                  "en": s["text"].strip(), "ja": ja[n], "塊": 塊i[n]} for n, s in enumerate(文)]}
        DATA[名] = {k: t[k] for k in ("話者", "題", "年", "wpm", "出典", "音声")} | {"区間": 区間}
    return DATA


if __name__ == "__main__":
    DATA = データを作る()
    # 単語をタップしたときの意味（辞書.py が作る）。英文を直したら 辞書.py も回し直す
    辞書 = json.loads((根 / "辞書.json").read_text())
    雛形 = (根 / "雛形.html").read_text()
    for 印 in ("__DATA__", "__DICT__"):
        if 印 not in 雛形:
            raise SystemExit(f"雛形.html に {印} が無い")
    (根 / "index.html").write_text(雛形.replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
                                   .replace("__DICT__", json.dumps(辞書, ensure_ascii=False, separators=(",", ":"))))
    文数 = sum(len(区["文"]) for t in DATA.values() for 区 in t["区間"].values())
    print(f"index.html を作った（{len(DATA)} トーク・{文数} 文・辞書 {len(辞書)} 語）")
