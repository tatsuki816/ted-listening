#!/usr/bin/env python3
"""新しいトークを足すときの下ごしらえ。TED の英文を文に割り、全体の音声で時刻を合わせ、区間ごとに音声を切る。

  ~/音声入力/.venv/bin/python3 トーク準備.py treasure          # 確認だけ（区間ごとの文数と一致率）
  ~/音声入力/.venv/bin/python3 トーク準備.py treasure --書く    # audio/<名>/N.mp3 と トーク/<名>/ を書く

材料は 元データ_<名>/ に置く（gitignore 済み。大きいので push しない）
  全体.mp3       TED のページにある mp4 から ffmpeg で抜いた音声（YouTube は 403 で落ちた）
  transcript.json TED の transcript ページの __NEXT_DATA__ にある cues
  単語.json      whisper（large-v3-turbo）の単語ごとの時刻。無ければ回して作る
Tim Urban（urban）は前からある vault のデータを使うので、これは通さない。
2026-10-24：Julian Treasure を足すときに作った。
"""
import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

根 = Path(__file__).parent
モデル = "mlx-community/whisper-large-v3-turbo"
前の余白 = 0.8
後の余白 = 1.2
文頭の余白 = 0.12
文末の余白 = 0.25

# 区間の切れ目。(その区間の最初の文の番号, 見出し)。文の番号は 英文.json の0始まり
区間の割り方 = {
    "treasure": [(0, "はじめに・悪い癖1〜3"), (19, "悪い癖4〜7"), (40, "HAIL"),
                 (62, "声の道具：register と timbre"), (82, "prosody・pace・pitch・volume"),
                 (107, "ウォームアップと締め")],
}


def 語に割る(s):
    s = s.lower().replace("’", "'").replace("—", " ").replace("–", " ").replace("--", " ")
    return re.findall(r"[a-z0-9']+", s)


def 文に割る(cues):
    txt = " ".join(c["text"].replace("\n", " ") for c in cues)
    # 笑い・拍手・声色の注記は話していないので消す
    txt = re.sub(r"\((Laughter|Applause|Laughs?|Loud|Higher pitch|Singing)\)", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    文 = re.split(r'(?<=[.?!])\s+(?=["“(]?[A-Z0-9])|(?<=[.?!]["”])\s+', txt)
    return [s.strip() for s in 文 if s.strip()]


def 単語(名, 音声):
    p = 根 / f"元データ_{名}/単語.json"
    if not p.exists():
        import mlx_whisper
        r = mlx_whisper.transcribe(str(音声), path_or_hf_repo=モデル, language="en",
                                   word_timestamps=True, condition_on_previous_text=False)
        p.write_text(json.dumps([{"w": w["word"], "s": float(w["start"]), "e": float(w["end"])}
                                 for seg in r["segments"] for w in seg.get("words", [])]))
    return [(t, w["s"], w["e"]) for w in json.loads(p.read_text()) for t in 語に割る(w["w"])]


def main():
    名 = sys.argv[1]
    書く = "--書く" in sys.argv
    元 = 根 / f"元データ_{名}"
    音声 = 元 / "全体.mp3"
    文 = 文に割る(json.loads((元 / "transcript.json").read_text()))
    聞 = 単語(名, 音声)

    正 = [(t, i) for i, s in enumerate(文) for t in 語に割る(s)]
    時 = {}
    sm = SequenceMatcher(None, [a for a, _ in 正], [a for a, _, _ in 聞], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                時[i1 + k] = 聞[j1 + k][1:]

    始終 = []
    for i, s in enumerate(文):
        位置 = [k for k, (_, n) in enumerate(正) if n == i]
        当たり = [時[k] for k in 位置 if k in 時]
        if not 当たり:
            始終.append(None)   # Brrrr. のような声だけの文。前後の文の間で埋める
            continue
        始終.append([当たり[0][0] - 文頭の余白, 当たり[-1][1] + 文末の余白, len(当たり) / len(位置)])
    for i, x in enumerate(始終):
        if x is None:
            前 = 始終[i - 1][1]
            次 = next(y[0] for y in 始終[i + 1:] if y is not None)
            始終[i] = [前, 次, 0.0]
            print(f"  {i}文目は音声と合う単語が無いので、前後の文の間（{前:.1f}〜{次:.1f}秒）にした：{文[i]}")
    # 余白を足して隣の文に食い込んだら、間で分ける
    for i in range(len(始終) - 1):
        if 始終[i][1] > 始終[i + 1][0]:
            中 = (始終[i][1] - 文末の余白 + 始終[i + 1][0] + 文頭の余白) / 2
            始終[i][1] = 始終[i + 1][0] = 中

    割 = 区間の割り方[名] + [(len(文), None)]
    if 書く:
        (根 / f"audio/{名}").mkdir(parents=True, exist_ok=True)
        (根 / f"トーク/{名}/データ").mkdir(parents=True, exist_ok=True)
        (根 / f"トーク/{名}/単語の時刻").mkdir(parents=True, exist_ok=True)
        (根 / f"トーク/{名}/英文.json").write_text(json.dumps(文, ensure_ascii=False, indent=0))
    for n in range(len(割) - 1):
        a, b = 割[n][0], 割[n + 1][0]
        切始 = max(0.0, 始終[a][0] - 前の余白)
        切終 = 始終[b - 1][1] + 後の余白
        if b < len(文):
            切終 = min(切終, 始終[b][0])
        低 = [i for i in range(a, b) if 始終[i][2] < 0.8]
        print(f"区間{n+1} {割[n][1]}：{b-a}文 {切始:.1f}〜{切終:.1f}秒（{切終-切始:.0f}秒） 一致率が低い文 {低 or 'なし'}")
        if not 書く:
            continue
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{切始:.3f}", "-to", f"{切終:.3f}", "-i", str(音声),
                        "-ac", "1", "-b:a", "96k", str(根 / f"audio/{名}/{n+1}.mp3")], check=True)
        データ = [{"start": round(始終[i][0] - 切始, 2), "end": round(始終[i][1] - 切始, 2), "text": 文[i]}
                 for i in range(a, b)]
        (根 / f"トーク/{名}/データ/区間{n+1}.json").write_text(json.dumps(データ, ensure_ascii=False, indent=0))
        語 = [[t, round(s - 切始, 3), round(e - 切始, 3)] for t, s, e in 聞 if 切始 <= s < 切終]
        (根 / f"トーク/{名}/単語の時刻/区間{n+1}.json").write_text(json.dumps(語, ensure_ascii=False))
    if not 書く:
        print("確認だけ。書くなら --書く")


if __name__ == "__main__":
    main()
