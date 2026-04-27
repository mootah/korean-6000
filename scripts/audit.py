#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
国立国語院 6000語 CSV から「手直し候補件数」を洗い出すスクリプト

入力CSVフィールド:
rank, word, pos, def, level

想定区切り:
- TSV（タブ区切り）推奨
- CSV（カンマ区切り）でも可

目的:
1. 同一語幹で複数番号がある語（걷다01, 걷다02 ...）を抽出
2. 풀이が漢字語だけで機械処理しやすい語を除外
3. 풀이に用例ハングルを含む語を「手直し候補」として抽出
4. 件数集計

使い方:
python audit.py vocab.csv
python audit.py vocab.tsv --delimiter tab
"""

import csv
import re
import argparse
from collections import defaultdict

# -----------------------------
# 正規表現
# -----------------------------
RE_NUMBER_SUFFIX = re.compile(r"^(.*?)(\d{2})$")
RE_HANJA = re.compile(r"[一-龯㐀-䶵]")
RE_HANGUL = re.compile(r"[가-힣]")

# -----------------------------
# 基本関数
# -----------------------------
def split_word(word: str):
    """
    걷다02 -> ('걷다', '02')
    """
    word = word.strip()
    m = RE_NUMBER_SUFFIX.match(word)
    if m:
        return m.group(1), m.group(2)
    return word, None


def has_hanja(text: str):
    return bool(RE_HANJA.search(text or ""))


def has_hangul(text: str):
    return bool(RE_HANGUL.search(text or ""))


def classify_puri(text: str):
    """
    hanja  : 漢字あり（混在含む）
    hangul : ハングルのみ
    other  : 英語、空欄等
    """
    text = (text or "").strip()

    if has_hanja(text):
        return "hanja"
    elif has_hangul(text):
        return "hangul"
    return "other"


# -----------------------------
# CSV読み込み
# -----------------------------
def load_rows(path, delimiter):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            reader = csv.DictReader(f, delimiter="\t")
        else:
            reader = csv.DictReader(f)
        return list(reader)


# -----------------------------
# メイン
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("-d", "--delimiter", choices=["csv", "tab"], default="tab")
    parser.add_argument("-o", "--output", default="manual_fix_candidates.csv")
    args = parser.parse_args()

    rows = load_rows(args.file, args.delimiter)

    groups = defaultdict(list)

    for row in rows:
        base, num = split_word(row["word"])
        row["_base"] = base
        row["_num"] = num
        groups[base].append(row)

    total_groups = 0
    candidate_groups = 0
    candidate_rows = []

    for base, g in groups.items():
        numbered = [x for x in g if x["_num"] is not None]

        # 同音異義語グループ
        if len(numbered) >= 2:
            total_groups += 1

            # 漢字なし行だけ抽出
            manual_rows = [
                r for r in numbered
                if classify_puri(r["def"]) == "hangul"
            ]

            if manual_rows:
                candidate_groups += 1
                candidate_rows.extend(manual_rows)

    # 出力
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "base_word",
            "rank",
            "word",
            "pos",
            "pos_name",
            "pos_ja",
            "def",
            "level"
        ])

        for r in candidate_rows:
            writer.writerow([
                r["_base"],
                r["rank"],
                r["word"],
                r["pos"],
                r["pos_name"],
                r["pos_ja"],
                r["def"],
                r["level"]
            ])

    # 集計
    print("==== 集計結果 ====")
    print(f"全データ件数: {len(rows):,}")
    print(f"番号付き同音異義語グループ数: {total_groups:,}")
    print(f"手直し候補グループ数: {candidate_groups:,}")
    print(f"手直し候補語数(漢字あり除外): {len(candidate_rows):,}")
    print(f"出力ファイル: {args.output}")


if __name__ == "__main__":
    main()

