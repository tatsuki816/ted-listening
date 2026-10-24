#!/usr/bin/env python3
"""1文を、リピーティングで言い返せる長さ（3〜6語くらい）の意味のかたまりに区切り、それぞれの時刻を付ける。

  ~/音声入力/.venv/bin/python3 かたまり.py          # 区切って かたまり.json を書く
  ~/音声入力/.venv/bin/python3 かたまり.py --見る   # 区切り方を全部表示する（書き込まない）

トークが増えたら下の トーク に足す。かたまり.json は {トーク名: {区間: [...]}} の形。

whisper の単語ごとの時刻は 単語の時刻/区間N.json に貯める（2回目からは whisper を回さない。
音声を切り直したらこのフォルダを消してから回す）。
区切る場所は、句読点の後・接続詞や関係詞の前・話し手が息を継いだ所。長すぎるかたまりは前置詞の前で割る。
2026-10-13：シャドーイングが聞き取れず意味も追えないので、リピーティング用に作った（本人の相談）。
"""
import json
import re
import statistics
import sys
from difflib import SequenceMatcher
from pathlib import Path

根 = Path(__file__).parent
# トークごとの置き場。urban は前からある vault のデータ、treasure 以降は トーク準備.py が作る
トーク = {
    "urban": {"データ": Path.home() / "Documents/obsidian/法政大学2年/英語ライティング/リスニング/データ",
              "単語": 根 / "単語の時刻", "音声": "audio/{n}.mp3", "区間数": 5},
    "treasure": {"データ": 根 / "トーク/treasure/データ", "単語": 根 / "トーク/treasure/単語の時刻",
                 "音声": "audio/treasure/{n}.mp3", "区間数": 6},
}
モデル = "mlx-community/whisper-large-v3-turbo"

# この語の前で切ってよい（後ろに節や句が続く目印）
前で切る語 = {"and", "but", "because", "so", "that", "which", "who", "whom", "whose", "when", "where",
            "while", "if", "than", "or", "as", "until", "before", "after", "since", "though", "although",
            "unless", "whether", "how", "what", "why", "then"}
# 長すぎるときに限り、この前で切る
前置詞 = {"in", "on", "at", "for", "with", "about", "from", "into", "to", "by", "over", "through", "without"}
# この語の後ろでは切らない（次の語と一緒に言う語）
結び語 = {"a", "an", "the", "of", "to", "my", "your", "his", "her", "our", "their", "its", "this", "these",
         "those", "very", "not", "no", "every", "some", "any", "all", "much", "more", "most", "i", "we", "you",
         "they", "he", "she", "it", "is", "are", "was", "were", "be", "been", "am", "will", "would", "could",
         "should", "can", "have", "has", "had", "do", "does", "did", "don't", "doesn't", "didn't", "i'm",
         "i'd", "we're", "you're", "it's", "that's", "there's", "just", "really", "kind", "in", "on", "at",
         "for", "with", "from", "by", "about", "into", "than", "as", "and", "or", "but", "if", "when",
         "because", "so", "that", "which", "who", "what", "how", "where", "two", "one", "three", "first",
         "little", "half", "like", "normal", "entire", "single", "only", "hard", "other", "last", "few",
         "new", "big", "same", "take"}
# 無理に割るとき、この語の前では割らない
小辞 = {"up", "out", "off", "down", "it", "them", "him", "her", "me", "us", "on", "in", "back"}
最短 = 3        # これより短いかたまりは作らない（句読点の後だけは2語でも切る）
最長 = 7        # これを超えそうなら無理にでも切る
息継ぎ = 0.4    # 単語の間がこれ以上空いていたら区切りの候補（0.25 だと wakes / up のような句動詞の途中で割れた）
前に足す = 0.08
後に足す = 0.15


def 語に割る(s):
    s = s.lower().replace("’", "'").replace("—", " ").replace("–", " ").replace("--", " ")
    return re.findall(r"[a-z0-9']+", s)


def 単語の時刻(名, 区間):
    単語の置き場 = トーク[名]["単語"]
    p = 単語の置き場 / f"区間{区間}.json"
    if p.exists():
        return json.loads(p.read_text())
    import mlx_whisper
    r = mlx_whisper.transcribe(str(根 / トーク[名]["音声"].format(n=区間)), path_or_hf_repo=モデル, language="en",
                               word_timestamps=True, condition_on_previous_text=False)
    聞 = [[t, round(w["start"], 3), round(w["end"], 3)]
         for seg in r["segments"] for w in seg.get("words", []) for t in 語に割る(w["word"])]
    単語の置き場.mkdir(exist_ok=True)
    p.write_text(json.dumps(聞, ensure_ascii=False))
    return 聞


def 区切る(名, 区間):
    文 = json.loads((トーク[名]["データ"] / f"区間{区間}.json").read_text())
    聞 = 単語の時刻(名, 区間)

    # 表示用の語（空白区切り）と、照合用の語（語に割る）の対応を作る
    表 = []   # 文ごとに [(表示の語, [照合の語の通し番号])]
    正 = []
    for s in 文:
        行 = []
        for 語 in s["text"].split():
            番 = []
            for t in 語に割る(語):
                番.append(len(正)); 正.append(t)
            行.append((語, 番))
        表.append(行)

    時 = {}
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, 正, [a for a, _, _ in 聞], autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                時[i1 + k] = (聞[j1 + k][1], 聞[j1 + k][2])
    一致率 = len(時) / len(正)

    結果 = []
    for 文番, (s, 行) in enumerate(zip(文, 表)):
        # 語ごとの (始, 終)。合わなかった語は None
        語時 = []
        for _, 番 in 行:
            当 = [時[n] for n in 番 if n in 時]
            語時.append((当[0][0], 当[-1][1]) if 当 else None)

        def 素(語):
            return re.sub(r"[^a-z']", "", 語.lower())

        def 句読点で終わる(j):
            return bool(re.search(r"[,;:—–?!.]$|--$", 行[j][0])) or 行[j][0] in ("—", "–", "--")

        def 次の句読点までの語数(j):
            n = 0
            for k in range(j, len(行)):
                n += 1
                if 句読点で終わる(k):
                    break
            return n

        def 自然に切れるか(j, 長さ):
            """j 語目の後ろで、言い返しやすい切れ目になっているか"""
            if len(行) - j - 1 < 2:
                return False
            if 句読点で終わる(j):
                return 長さ >= 2
            if 長さ < 最短 or 素(行[j][0]) in 結び語:
                return False
            次 = 素(行[j + 1][0])
            if 次 in ("and", "or"):
                # easy / and fun のような短い並びは割らない
                return 次の句読点までの語数(j + 1) >= 4
            if 次 in 前で切る語:
                return True
            return bool(語時[j] and 語時[j + 1] and 語時[j + 1][0] - 語時[j][1] >= 息継ぎ)

        def 無理に割る位置(頭, 尻):
            """頭〜尻 が長すぎるとき、どこの後ろで割るか。良い所が無ければ None"""
            候補 = []
            for j in range(頭 + 2, 尻):
                前, 次 = 行[j][0], 行[j + 1][0]
                if 素(前) in 結び語 or 素(前).endswith("'s"):
                    continue   # the procrastinator's / only のような所有格の後ろも割らない
                if 素(次) in 小辞:
                    continue   # wakes / up・got / it のような動詞とその後ろの小さい語は割らない
                if 前[:1].isupper() and 次[:1].isupper() and j > 0:
                    continue   # Dark Playground のような固有名詞の途中
                点 = 0.0
                if 素(次) in 前で切る語:
                    点 += 3
                elif 素(次) in 前置詞:
                    点 += 2
                if 語時[j] and 語時[j + 1]:
                    点 += min(1.5, (語時[j + 1][0] - 語時[j][1]) * 5)
                点 -= abs((j - 頭 + 1) - 4) * 0.3
                候補.append((点, j))
            return max(候補)[1] if 候補 else None

        塊 = []   # [始めの語, 終わりの語]
        頭 = 0
        j = 0
        while j < len(行) - 1:
            長さ = j - 頭 + 1
            if 自然に切れるか(j, 長さ):
                塊.append((頭, j)); 頭 = j + 1
            elif 長さ >= 最長:
                k = 無理に割る位置(頭, j + 1)
                if k is not None:
                    塊.append((頭, k)); 頭 = k + 1
            j += 1
        塊.append((頭, len(行) - 1))
        # 最後が1語だけなら前にくっつける
        if len(塊) > 1 and 塊[-1][1] - 塊[-1][0] == 0:
            a, _ = 塊[-2]; 塊[-2:] = [(a, len(行) - 1)]

        # 時刻。かたまりの中で合った語の最初と最後。何も合わなければ文の中で語数で按分
        出 = []
        全語 = len(行)
        for a, b in 塊:
            当 = [語時[k] for k in range(a, b + 1) if 語時[k]]
            if 当:
                始, 終 = 当[0][0], 当[-1][1]
            else:
                幅 = s["end"] - s["start"]
                始, 終 = s["start"] + 幅 * a / 全語, s["start"] + 幅 * (b + 1) / 全語
            出.append({"en": " ".join(w for w, _ in 行[a:b + 1]), "s": 始, "e": 終})
        # 余白を足し、前後と重ならないようにし、文の範囲に収める
        for k, c in enumerate(出):
            c["s"] = s["start"] if k == 0 else max(出[k - 1]["e"], c["s"] - 前に足す)
            c["e"] = s["end"] if k == len(出) - 1 else c["e"] + 後に足す
        for k in range(len(出) - 1):
            if 出[k]["e"] > 出[k + 1]["s"]:
                中 = (出[k]["e"] - 後に足す + 出[k + 1]["s"]) / 2
                出[k]["e"] = 出[k + 1]["s"] = max(出[k]["s"] + 0.2, 中)
        結果.append([{"en": c["en"], "s": round(c["s"], 2), "e": round(c["e"], 2)} for c in 出])
    return 結果, 一致率


if __name__ == "__main__":
    全部 = {}
    語数 = []
    for 名, 設定 in トーク.items():
        全部[名] = {}
        for 区間 in range(1, 設定["区間数"] + 1):
            結果, 一致率 = 区切る(名, 区間)
            全部[名][str(区間)] = 結果
            塊数 = sum(len(r) for r in 結果)
            語数 += [len(c["en"].split()) for r in 結果 for c in r]
            壊れ = [(i + 1, c["en"]) for i, r in enumerate(結果) for c in r if c["e"] - c["s"] < 0.25]
            print(f"{名} 区間{区間}: {len(結果)}文 → {塊数}かたまり  単語の一致率 {一致率:.0%}  短すぎる時刻 {壊れ or 'なし'}")
            if "--見る" in sys.argv:
                for i, r in enumerate(結果):
                    print(f"  {i+1:>2}  " + " / ".join(c["en"] for c in r))
    print(f"1かたまりの語数  中央値 {statistics.median(語数)}  最大 {max(語数)}  1語だけ {語数.count(1)}")
    if "--見る" not in sys.argv:
        (根 / "かたまり.json").write_text(json.dumps(全部, ensure_ascii=False, indent=0))
        print("かたまり.json を書いた")
