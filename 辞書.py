#!/usr/bin/env python3
"""ページに出てくる単語の意味を引いて 辞書.json を作る。単語をタップしたときに出す。

  python3 辞書.py

辞書は EJDict（kujirahand、CC0。元データ_辞書/ejdict.zip に置く。gitignore 済み）。
ページの全トークの英文から単語を集め、ページ側と同じ形に正規化して引く。
見つからなければ 短縮形 → 不規則変化 → 語尾を外す → ハイフンで割る の順に試す。
トークを足したり英文を直したら、これを回してから 組み立て.py を回す。
2026-10-24：単語をタップすると意味が出る機能のために作った（本人の希望）。
"""
import json
import re
import zipfile
from pathlib import Path

根 = Path(__file__).parent

短縮形 = {"i'm": "I am", "i've": "I have", "i'd": "I would / I had", "i'll": "I will", "you're": "you are",
         "you've": "you have", "you'd": "you would / you had", "you'll": "you will", "we're": "we are",
         "we've": "we have", "we'd": "we would / we had", "we'll": "we will", "they're": "they are",
         "they've": "they have", "they'd": "they would / they had", "they'll": "they will", "he's": "he is / he has",
         "she's": "she is / she has", "it's": "it is / it has", "that's": "that is", "there's": "there is",
         "here's": "here is", "what's": "what is", "who's": "who is", "let's": "let us（〜しよう）",
         "don't": "do not", "doesn't": "does not", "didn't": "did not", "can't": "cannot", "couldn't": "could not",
         "won't": "will not", "wouldn't": "would not", "shouldn't": "should not", "isn't": "is not",
         "aren't": "are not", "wasn't": "was not", "weren't": "were not", "haven't": "have not",
         "hasn't": "has not", "hadn't": "had not", "it'll": "it will", "that'll": "that will", "he'd": "he would / he had",
         "she'd": "she would / she had", "somebody's": "somebody is / somebody has", "ain't": "am not / is not",
         "y'all": "you all", "gonna": "going to", "wanna": "want to"}

# EJDict に無い語（固有名詞・造語・声だけの語・新しい語）。辞書.py の最後に出る「見つからない」を見て足す
手書き = {"ahhhh": "あ〜（ため息の声）", "ahhhhh": "あ〜（ため息の声）", "arousal": "気持ちの高ぶり、興奮",
         "bieber's": "Justin Bieber（歌手）の", "blamethrower": "責任放射器（flamethrower＝火炎放射器のもじり。責任を周りに押しつける人）",
         "blog": "ブログ", "brrrr": "ブルル（唇を震わせる声）", "brrrrrrrrrr": "ブルルル（唇を震わせる声）",
         "emailing": "メールを送ること", "emails": "メール（複数）", "entrepreneurial": "起業家的な、起業の",
         "feynman": "Richard Feynman（物理学者）", "google": "グーグル（検索）", "justin": "Justin（人名）",
         "kerrigan": "Nancy Kerrigan（フィギュアスケート選手）", "monotonic": "単調な、一本調子の",
         "mri": "MRI（体の中を撮る検査機械）", "nancy": "Nancy（人名）", "negativity": "否定的な態度、後ろ向きさ",
         "non-procrastinator": "先延ばしをしない人", "non-procrastinators": "先延ばしをしない人たち",
         "procrastinator": "先延ばしにする人", "procrastinator's": "先延ばしにする人の",
         "procrastinators": "先延ばしにする人たち", "richard": "Richard（人名）", "rrrrrrr": "ルルル（巻き舌の音）",
         "sodcasting": "周りに聞こえるように大音量で音を流すこと（迷惑な行為として話者が使った語）",
         "til": "till（〜まで）のくだけた形", "tim": "Tim（人名。話者の Tim Urban）", "tonya": "Tonya Harding（フィギュアスケート選手）",
         "u.k": "イギリス（the U.K.）", "ums": "「えーと」という言いよどみ", "website": "ウェブサイト",
         "weeeaawww": "ウィーオー（高い声から低い声へ下げる発声練習）", "wikipedia": "ウィキペディア", "youtube": "YouTube",
         # 辞書の最初の意味がトークの意味とずれる語（トークでの意味を先に出す）
         "prosody": "抑揚、話し方の調子（Treasure のトークの意味）／韻律論", "sing-song": "歌うような抑揚、節をつけた調子",
         "register": "声域（Treasure のトークの意味）／登録する、名簿", "falsetto": "裏声",
         # 辞書の並びだと珍しい意味が先に出る基本語
         "a": "1つの、ある（数えられる名詞の前）", "an": "1つの、ある（母音で始まる語の前の a）", "am": "be の現在形（I am）",
         "well": "まあ、ええと（話のつなぎ）／よく、上手に／井戸", "just": "ちょうど、ただ〜だけ、ほんの／正しい",
         "so": "だから、それで／とても、そんなに／そのように", "right": "そうだよね？（確認）／正しい／右",
         "like": "〜のような、〜みたいに／好む", "kind": "種類（kind of＝ちょっと、なんとなく）／親切な",
         "actually": "実は、実際には", "really": "本当に、すごく", "pretty": "かなり、けっこう／かわいい",
         "mean": "意味する、〜のつもりで言う（I mean＝つまり）／意地悪な", "thing": "もの、こと",
         "way": "方法、やり方／道／（強調）ずっと、はるかに", "got": "get の過去・過去分詞（have got＝持っている）"}

不規則 = {"went": "go", "said": "say", "made": "make", "took": "take", "taken": "take", "got": "get",
         "gotten": "get", "thought": "think", "came": "come", "knew": "know", "known": "know", "saw": "see",
         "seen": "see", "told": "tell", "felt": "feel", "left": "leave", "found": "find", "gave": "give",
         "given": "give", "began": "begin", "begun": "begin", "became": "become", "ran": "run", "wrote": "write",
         "written": "write", "spent": "spend", "kept": "keep", "heard": "hear", "met": "meet", "sat": "sit",
         "stood": "stand", "understood": "understand", "brought": "bring", "bought": "buy", "caught": "catch",
         "taught": "teach", "held": "hold", "meant": "mean", "built": "build", "sent": "send", "lost": "lose",
         "paid": "pay", "did": "do", "done": "do", "does": "do", "has": "have", "had": "have", "is": "be",
         "are": "be", "was": "be", "were": "be", "been": "be", "am": "be", "children": "child", "people": "person",
         "men": "man", "women": "woman", "feet": "foot", "teeth": "tooth", "mice": "mouse", "better": "good",
         "best": "good", "worse": "bad", "worst": "bad", "fell": "fall", "fallen": "fall", "woke": "wake",
         "drove": "drive", "driven": "drive", "ate": "eat", "eaten": "eat", "threw": "throw", "thrown": "throw",
         "grew": "grow", "grown": "grow", "flew": "fly", "spoke": "speak", "spoken": "speak", "chose": "choose",
         "chosen": "choose", "broke": "break", "broken": "break", "forgot": "forget", "forgotten": "forget",
         "led": "lead", "slept": "sleep", "sold": "sell", "won": "win", "shook": "shake", "hid": "hide",
         "hidden": "hide", "rode": "ride", "rose": "rise", "risen": "rise", "sang": "sing", "sung": "sing"}


def 正規化(語):
    # ページ側（雛形.html の 正規化）と同じ形にそろえる
    k = 語.lower().replace("’", "'").replace("‘", "'")
    k = re.sub(r"^[^a-z0-9']+|[^a-z0-9']+$", "", k)
    return k.strip("'")


def 意味に割る(本文):
    出 = []
    for m in 本文.split(" / "):
        m = re.sub(r"《[^》]*》|〈[^〉]*〉", "", m).replace("『", "").replace("』", "").strip(" ,;")
        if m and m not in 出:
            出.append(m if len(m) <= 40 else m[:39] + "…")
        if len(出) >= 3:
            break
    return 出


def 語尾を外す(k):
    候 = []
    if k.endswith("'s"):
        候.append(k[:-2])
    for 尾, 足す in (("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"), ("ily", "y"), ("es", ""), ("s", ""),
                    ("ed", ""), ("ed", "e"), ("d", ""), ("ing", ""), ("ing", "e"), ("er", ""), ("er", "e"),
                    ("est", ""), ("est", "e"), ("ly", ""), ("ness", ""), ("ment", "")):
        if k.endswith(尾) and len(k) - len(尾) >= 2:
            根語 = k[:-len(尾)] + 足す
            候.append(根語)
            # stopped → stop、running → run のような子音の重ね
            if not 足す and len(根語) >= 3 and 根語[-1] == 根語[-2] and 根語[-1] not in "aeiouls":
                候.append(根語[:-1])
    return 候


def main():
    z = zipfile.ZipFile(根 / "元データ_辞書/ejdict.zip")
    辞 = {}
    小文字で入れた = set()
    for n in z.namelist():
        if re.search(r"/src/[a-z]\.txt$", n):
            for 行 in z.read(n).decode("utf-8").splitlines():
                if "\t" in 行:
                    見, 本 = 行.split("\t", 1)
                    for 見出し in 見.split(","):
                        見出し = 見出し.strip()
                        # 小文字の見出しを優先する。WHO（世界保健機関）が who を、US が us を上書きしていた
                        if 見出し.lower() not in 辞 or 見出し == 見出し.lower():
                            if 見出し == 見出し.lower() and 見出し in 小文字で入れた:
                                辞[見出し] += " / " + 本   # 同じ見出しが品詞ごとに複数行あるのはつなぐ
                                continue
                            辞[見出し.lower()] = 本
                            if 見出し == 見出し.lower():
                                小文字で入れた.add(見出し)

    import 組み立て   # import しただけでは index.html を書かない
    語たち = set()
    for t in 組み立て.データを作る().values():
        for 区 in t["区間"].values():
            for s in 区["文"]:
                for 語 in s["en"].split():
                    k = 正規化(語)
                    if k and re.search(r"[a-z]", k):
                        語たち.add(k)

    出 = {}
    無い = []
    for k in sorted(語たち):
        if k in 手書き:
            出[k] = {"h": k, "m": [手書き[k]]}
            continue
        if k in 短縮形:
            出[k] = {"h": k, "m": [短縮形[k] + " の短縮形"]}
            continue
        候 = [k]
        if k in 不規則:
            候.append(不規則[k])
        候 += 語尾を外す(k)
        当 = next((c for c in 候 if c in 辞), None)
        if 当:
            出[k] = {"h": 当, "m": 意味に割る(辞[当])}
            continue
        if "-" in k:
            部 = [p for p in k.split("-") if p in 辞]
            if 部:
                出[k] = {"h": k, "m": [(p + "：" + "、".join(意味に割る(辞[p])[:2]))[:34] for p in 部]}
                continue
        無い.append(k)
    (根 / "辞書.json").write_text(json.dumps(出, ensure_ascii=False, separators=(",", ":")))
    print(f"辞書.json を書いた：{len(語たち)}語のうち {len(出)}語に意味あり。見つからない {len(無い)}語：{' '.join(無い)}")


if __name__ == "__main__":
    main()
