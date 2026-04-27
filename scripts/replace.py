#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
풀이 内の ~ を base_word に置換するスクリプト

入力例:
base_word,rank,word,pos,def,level
가리다,2913,가리다02,동,시야를 ~,B

出力例:
가리다,2913,가리다02,동,시야를 가리다,B

使い方:
python replace.py input.csv
python replace.py input.csv -o output.csv
python replace.py input.tsv --delimiter tab
"""

import csv
import argparse
import re

RE_NUMBER_SUFFIX = re.compile(r"^(.*?)(\d{2})$")

def split_word(word: str):
    """
    걷다02 -> ('걷다', '02')
    """
    word = word.strip()
    m = RE_NUMBER_SUFFIX.match(word)
    if m:
        return m.group(1), m.group(2)
    return word, None

def load_rows(path, delimiter):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            reader = csv.DictReader(f, delimiter="\t")
        else:
            reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def save_rows(path, rows, fieldnames, delimiter):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            writer = csv.DictWriter(
                f, fieldnames=fieldnames, delimiter="\t"
            )
        else:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(rows)


def replace_tilde(rows):
    changed = 0

    for row in rows:
        base_word, _ = split_word(row["word"].strip())
        puri = row["def"]

        if "~" in puri:
            row["def"] = puri.replace("~", base_word)
            changed += 1

    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument(
        "-d",
        "--delimiter",
        choices=["csv", "tab"],
        default="tab"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="replaced_output.csv"
    )

    args = parser.parse_args()

    rows, fieldnames = load_rows(args.file, args.delimiter)
    changed = replace_tilde(rows)
    save_rows(args.output, rows, fieldnames, args.delimiter)

    print("==== 完了 ====")
    print(f"総件数: {len(rows):,}")
    print(f"置換件数: {changed:,}")
    print(f"出力: {args.output}")


if __name__ == "__main__":
    main()
