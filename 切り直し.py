#!/usr/bin/env python3
"""全体の音声で132文の時刻を取り直し、区間の音声を文の切れ目で切り直す。

  ~/音声入力/.venv/bin/python3 切り直し.py          # 確認だけ
  ~/音声入力/.venv/bin/python3 切り直し.py --書く    # 音源/区間N.mp3 と データ/区間N.json を書き換える

元の区間は TED の字幕の時刻で切っていて、実際の話より約5秒早かった。そのため字幕が先に出て、
区間の最後の数文は次の区間の音声に入っていた（2026-09-24 本人指摘・実測）。
区間の文の割り当て（どの文がどの区間か）は変えない。音声の切り位置と時刻だけを直す。
"""
import json
import re
import statistics
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

import mlx_whisper

モデル = "mlx-community/whisper-large-v3-turbo"
元 = Path.home() / "Documents/obsidian/法政大学2年/英語ライティング/リスニング"
全体 = 元 / "音源/TimUrban_全体.mp3"
前の余白 = 0.8     # 区間の音声は最初の文の少し前から
後の余白 = 1.2     # 最後の文の少し後まで（笑いの頭）
文頭の余白 = 0.12
文末の余白 = 0.25


def 語に割る(s):
    s = s.lower().replace("’", "'").replace("—", " ").replace("–", " ").replace("--", " ")
    return re.findall(r"[a-z0-9']+", s)


def 全文():
    文 = []
    for k in range(1, 6):
        for s in json.loads((元 / f"データ/区間{k}.json").read_text()):
            文.append({"区間": k, "text": s["text"]})
    return 文


def 揃える(文):
    r = mlx_whisper.transcribe(str(全体), path_or_hf_repo=モデル, language="en",
                               word_timestamps=True, condition_on_previous_text=False)
    聞 = [(t, w["start"], w["end"]) for seg in r["segments"] for w in seg.get("words", []) for t in 語に割る(w["word"])]
    正 = [(t, i) for i, s in enumerate(文) for t in 語に割る(s["text"])]
    時 = {}
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, [a for a, _ in 正], [a for a, _, _ in 聞], autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                時[i1 + k] = 聞[j1 + k][1:]
    for i, s in enumerate(文):
        位置 = [k for k, (_, n) in enumerate(正) if n == i]
        当 = [時[k] for k in 位置 if k in 時]
        s["一致率"] = len(当) / max(len(位置), 1)
        s["始"], s["終"] = (当[0][0], 当[-1][1]) if 当 else (None, None)
    # 1語も合わなかった文は前後から埋める（起きなければ使われない）
    for i, s in enumerate(文):
        if s["始"] is None:
            前 = next((文[j]["終"] for j in range(i - 1, -1, -1) if 文[j]["終"] is not None), 0.0)
            後 = next((文[j]["始"] for j in range(i + 1, len(文)) if 文[j]["始"] is not None), 前 + 3)
            s["始"], s["終"] = 前, 後
    return 文


def 切る(文, 書く):
    全長 = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(全体)],
                               capture_output=True, text=True).stdout)
    for k in range(1, 6):
        群 = [s for s in 文 if s["区間"] == k]
        前区間の終 = max([s["終"] for s in 文 if s["区間"] == k - 1], default=0.0)
        次区間の始 = min([s["始"] for s in 文 if s["区間"] == k + 1], default=全長)
        頭 = max(前区間の終, 群[0]["始"] - 前の余白)
        尻 = min(次区間の始, 群[-1]["終"] + 後の余白)
        データ = []
        for i, s in enumerate(群):
            前の終 = 群[i - 1]["終"] if i else 頭
            次の始 = 群[i + 1]["始"] if i + 1 < len(群) else 尻
            データ.append({"start": round(max(前の終, s["始"] - 文頭の余白) - 頭, 2),
                           "end": round(min(次の始, s["終"] + 文末の余白) - 頭, 2),
                           "text": s["text"]})
        低 = [f"{i+1}文目{s['一致率']:.0%}" for i, s in enumerate(群) if s["一致率"] < 0.6]
        print(f"区間{k}: 全体の {頭:7.2f}〜{尻:7.2f} 秒（{尻-頭:5.1f}秒・{len(群)}文） 一致率の低い文 {低 or 'なし'}")
        if 書く:
            出 = 元 / f"音源/区間{k}.mp3"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(全体), "-ss", f"{頭:.3f}", "-to", f"{尻:.3f}",
                            "-map_metadata", "-1", "-c:a", "libmp3lame", "-b:a", "160k",
                            "-metadata", f"title=区間{k}", "-metadata", "artist=Tim Urban",
                            "-metadata", "album=TED Inside the Mind of a Master Procrastinator",
                            "-metadata", f"track={k}/5", "-metadata", "genre=English Listening", str(出)], check=True)
            (元 / f"データ/区間{k}.json").write_text(json.dumps(データ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    文 = 揃える(全文())
    print(f"全{len(文)}文  一致率の中央値 {statistics.median(s['一致率'] for s in 文):.0%}")
    切る(文, "--書く" in sys.argv)
    if "--書く" in sys.argv:
        print("書き換えた。時刻合わせ.py で区間ごとに検算すること")
