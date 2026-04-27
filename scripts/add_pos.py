#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
国立国語院 6000語 CSV に
- 品詞(韓国語正式名)
- 品詞(日本語)

の2列を追加するスクリプト

入力:
rank, word, pos, def, level

出力列:
rank, word, pos, pos_name, pos_ja, def, level

使い方:
python add_pos.py input.csv
python add_pos.py input.tsv -d tab
python add_pos.py input.csv -o output.csv
"""

import csv
import argparse

# --------------------------------
# 品詞マッピング
# --------------------------------
POS_MAP = {
    "동": ("동사", "動詞"),
    "명": ("명사", "名詞"),
    "의": ("의존 명사", "依存名詞"),
    "보": ("보조 용언", "補助用言"),
    "대": ("대명사", "代名詞"),
    "형": ("형용사", "形容詞"),
    "불": ("불완전 명사", "不完全名詞"),
    "부": ("부사", "副詞"),
    "관": ("관형사", "冠形詞"),
    "감": ("감탄사", "感動詞"),
}


def load_rows(path, delimiter):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            reader = csv.DictReader(f, delimiter="\t")
        else:
            reader = csv.DictReader(f)

        rows = list(reader)
        fields = reader.fieldnames

    return rows, fields


def add_columns(rows):
    for row in rows:
        code = row["pos"].strip()

        ko, ja = POS_MAP.get(code, ("未分類", "未分類"))

        row["pos_name"] = ko
        row["pos_ja"] = ja

    return rows


def reorder_fields(fields):
    return [
        "rank",
        "word",
        "pos",
        "pos_name",
        "pos_ja",
        "def",
        "level"
    ]


def save_rows(path, rows, fields, delimiter):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            writer = csv.DictWriter(
                f,
                fieldnames=fields,
                delimiter="\t"
            )
        else:
            writer = csv.DictWriter(
                f,
                fieldnames=fields
            )

        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument(
        "-d",
        "--delimiter",
        choices=["csv", "tab"],
        default="csv"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="pos_added.csv"
    )

    args = parser.parse_args()

    rows, fields = load_rows(args.file, args.delimiter)
    rows = add_columns(rows)
    out_fields = reorder_fields(fields)

    save_rows(args.output, rows, out_fields, args.delimiter)

    print("==== 完了 ====")
    print(f"件数: {len(rows):,}")
    print(f"出力: {args.output}")


if __name__ == "__main__":
    main()
