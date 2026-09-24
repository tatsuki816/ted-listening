#!/usr/bin/env python3
"""字幕の時刻を実際の音声に合わせ直す。

  ~/音声入力/.venv/bin/python3 時刻合わせ.py 1        # 区間1だけ（確認用。書き込まない）
  ~/音声入力/.venv/bin/python3 時刻合わせ.py 1 --書く  # 書き込む
  ~/音声入力/.venv/bin/python3 時刻合わせ.py all --書く

whisper に単語ごとの時刻を出させ、正解の英文の単語列と突き合わせる。
各文の開始 = その文で最初に一致した単語が鳴り始めた時刻、終了 = 最後に一致した単語が鳴り終わった時刻。
元の時刻は TED の字幕の区切りを文に割っただけのもので、話より先に字幕が出ていた（2026-09-24 本人指摘）。
データは Obsidian の vault のもの（書き取り.py と共有）なので、直すと両方に効く。
"""
import json
import re
import statistics
import sys
from difflib import SequenceMatcher
from pathlib import Path

import mlx_whisper

モデル = "mlx-community/whisper-large-v3-turbo"
元 = Path.home() / "Documents/obsidian/法政大学2年/英語ライティング/リスニング"
前に足す = 0.12   # 最初の子音が切れないよう、開始を少しだけ前へ
後に足す = 0.25   # 語尾の余韻を切らないよう、終了を少しだけ後ろへ


def 語に割る(s: str) -> list[str]:
    s = s.lower().replace("’", "'").replace("—", " ").replace("–", " ").replace("--", " ")
    return re.findall(r"[a-z0-9']+", s)


def 合わせる(区間: int) -> tuple[list, list]:
    文 = json.loads((元 / f"データ/区間{区間}.json").read_text())
    r = mlx_whisper.transcribe(str(元 / f"音源/区間{区間}.mp3"), path_or_hf_repo=モデル,
                               language="en", word_timestamps=True, condition_on_previous_text=False)
    聞 = []   # (語, 始, 終)
    for seg in r["segments"]:
        for w in seg.get("words", []):
            for t in 語に割る(w["word"]):
                聞.append((t, w["start"], w["end"]))

    正 = []   # (語, 文番号)
    for i, s in enumerate(文):
        正 += [(t, i) for t in 語に割る(s["text"])]

    時 = {}   # 正解の語の位置 → (始, 終)
    sm = SequenceMatcher(None, [a for a, _ in 正], [a for a, _, _ in 聞], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                時[i1 + k] = 聞[j1 + k][1:]

    新 = []
    for i, s in enumerate(文):
        位置 = [k for k, (_, n) in enumerate(正) if n == i]
        当たり = [時[k] for k in 位置 if k in 時]
        一致率 = len(当たり) / max(len(位置), 1)
        if 当たり:
            始, 終 = 当たり[0][0], 当たり[-1][1]
        else:
            始, 終 = s["start"], s["end"]   # 一語も合わなければ元のまま
        新.append({"start": 始, "end": 終, "text": s["text"], "一致率": round(一致率, 2)})

    # 前後の文と重ならないように余白を足す
    全長 = r["segments"][-1]["end"] if r["segments"] else 文[-1]["end"]
    for i, s in enumerate(新):
        前の終 = 新[i - 1]["end"] if i else 0.0
        次の始 = 新[i + 1]["start"] if i + 1 < len(新) else 全長 + 1
        s["start"] = round(max(前の終, s["start"] - 前に足す), 2)
        s["end"] = round(min(次の始, s["end"] + 後に足す), 2)
    return 文, 新


def 報告(区間, 旧, 新):
    差 = [n["start"] - o["start"] for o, n in zip(旧, 新)]
    低 = [f"{i+1}文目 {n['一致率']:.0%}" for i, n in enumerate(新) if n["一致率"] < 0.6]
    print(f"区間{区間}: 開始のずれ 中央値 {statistics.median(差):+.2f}秒 / 最大 {max(差, key=abs):+.2f}秒 / "
          f"一致率の低い文 {低 or 'なし'}")
    for i, (o, n) in enumerate(zip(旧, 新)):
        if i < 4 or abs(n["start"] - o["start"]) > 2:
            print(f"   {i+1:>2}  {o['start']:7.2f} → {n['start']:7.2f}  ({n['start']-o['start']:+.2f})  {n['text'][:48]}")


if __name__ == "__main__":
    対象 = range(1, 6) if sys.argv[1] == "all" else [int(sys.argv[1])]
    for 区間 in 対象:
        旧, 新 = 合わせる(区間)
        報告(区間, 旧, 新)
        if "--書く" in sys.argv:
            (元 / f"データ/区間{区間}.json").write_text(json.dumps(
                [{"start": n["start"], "end": n["end"], "text": n["text"]} for n in 新],
                ensure_ascii=False, indent=1))
            print(f"   → データ/区間{区間}.json を書いた")
