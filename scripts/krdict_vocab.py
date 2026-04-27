#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KRDict API を使って CSV に追加情報を付与するスクリプト

入力CSV:
rank,word,pos,pos_name,pos_ja,def,level

例:
898,가격03,명,명사,名詞,價格,B
36464,중식80,명,명사,名詞,中食. 중국 음식,C


--------------------------------
条件
--------------------------------
- def に漢字を含む行 または def にハングルを含まない行 のみ API検索
- word + pos 完全一致検索
- 検索結果から def の漢字一致エントリーを採用
- 漢字を含まない場合は検索結果の先頭エントリを採用

✅ 追加: 一行処理ごとにCSVに追記保存。途中で中断しても処理済みデータは失われません

--------------------------------
追加列
--------------------------------
target_code
word_grade
trans_word
link

--------------------------------
事前準備
--------------------------------
KRDict Open API キー取得:
https://krdict.korean.go.kr/openApi/openApiInfo

--------------------------------
使い方
--------------------------------
python krdict_vocab.py input.csv --api-key YOUR_KEY
python krdict_vocab.py input.csv --api-key YOUR_KEY -o output.csv
"""

import csv
import re
import time
import os
import argparse
import requests
import xml.etree.ElementTree as ET

API_URL = "https://krdict.korean.go.kr/api/search"

RE_HANJA = re.compile(r"[一-龯㐀-䶵]")
RE_HANGUL = re.compile(r"[가-힣]")
RE_SUFFIX = re.compile(r"^(.*?)(\d{2})$")

# --------------------------------
# CSV品詞略号 → API pos integer
# --------------------------------
POS_CODE_MAP = {
    "명": 1,   # 명사
    "대": 2,   # 대명사
    "수": 3,   # 수사
    "조": 4,   # 조사
    "동": 5,   # 동사
    "형": 6,   # 형용사
    "관": 7,   # 관형사
    "부": 8,   # 부사
    "감": 9,   # 감탄사
    "접": 10,  # 접사
    "의": 11,  # 의존 명사
    "보동": 12, # 보조 동사
    "보형": 13, # 보조 형용사

    # 既存CSV対応
    # "보": 12,
    "보": 13,
    # "불": 15,   # 품사 없음 に暫定
    "불": 0,   # 품사 없음 に暫定
}

WORD_GRADE = {
    "초급": "初級",
    "중급": "中級",
    "고급": "上級",
}

# --------------------------------
# Utility
# --------------------------------
def has_hanja(text):
    return bool(RE_HANJA.search(text or ""))

def has_hangul(text):
    return bool(RE_HANGUL.search(text or ""))

def classify_puri(text: str):
    """
    hanja  : 漢字あり（混在含む）
    hangul : ハングルのみ
    empty  : 空欄
    other  : 英語等
    """
    text = (text or "").strip()

    if text == "":
        return "empty"
    elif has_hanja(text):
        return "hanja"
    elif has_hangul(text):
        return "hangul"
    return "other"

def strip_number(word):
    """
    가격03 -> 가격
    """
    m = RE_SUFFIX.match(word.strip())
    if m:
        return m.group(1)
    return word.strip()


def normalize_def(text):
    """
    中食. 중국 음식 -> 中食
    """
    if not text:
        return ""

    text = text.strip()

    if ". " in text:
        return text.split(". ")[0].strip()

    if "." in text:
        return text.split(".")[0].strip()

    return text


def get_pos_code(pos_short):
    return POS_CODE_MAP.get(pos_short.strip(), 0)


def get_word_grade(word_grade):
    return WORD_GRADE.get(word_grade.strip(), "")

# --------------------------------
# Search
# --------------------------------
def search_krdict(api_key, word, pos_code):
    """
    advanced=y
    pos=array of integer
    """
    params = {
        "key": api_key,
        "q": word,

        # 日本語訳
        "translated": "y",
        "trans_lang": 2,

        # advanced
        "advanced": "y",

        # array of integer
        "pos": pos_code,
    }

    retry = 3
    for i in range(retry):
        try:
            r = requests.get(API_URL, params=params, timeout=20)
            r.raise_for_status()
            return r.text

        except requests.exceptions.RequestException as e:
            print("retry", i + 1, word, e)
            time.sleep(2)

    return None


# --------------------------------
# Parse XML
# --------------------------------
def parse_entries(xml_text):
    root = ET.fromstring(xml_text)
    items = []

    for item in root.findall(".//item"):
        row = {
            "word": item.findtext("word", default="").strip(),
            "pos": item.findtext("pos", default="").strip(),
            "target_code": item.findtext("target_code", default="").strip(),
            "word_grade": item.findtext("word_grade", default="").strip(),
            "link": item.findtext("link", default="").strip(),
            "origin": item.findtext("origin", default="").strip(),
            "trans_word": "",
            "trans_dfn": "",
        }

        trans = item.find(".//trans_word")
        if trans is not None and trans.text:
            row["trans_word"] = trans.text.strip()
        trans_dfn = item.find(".//trans_dfn")
        if trans_dfn is not None and trans_dfn.text:
            row["trans_dfn"] = trans_dfn.text.strip()

        items.append(row)

    return items


# --------------------------------
# Match
# --------------------------------
def pick_entry(entries, word, origin, use_origin_match):
    if use_origin_match:
        for e in entries:
            if e["word"] != word:
                continue

            if origin in e["origin"] or e["origin"] in origin:
                return e
        return None
    else:
        # 漢字を含まない場合は先頭の一致するwordエントリを返す
        for e in entries:
            if e["word"] == word:
                return e
        return None


# --------------------------------
# CSV
# --------------------------------
def load_csv(path, delimiter):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            reader = csv.DictReader(f, delimiter="\t")
        else:
            reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def init_output_csv(path, fields, delimiter):
    """出力CSVを初期化（ヘッダーのみ書き込み）"""
    file_exists = os.path.exists(path)
    
    if not file_exists:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            if delimiter == "tab":
                writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
            else:
                writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()


def append_row_to_csv(path, row, fields, delimiter):
    """1行だけCSVに追記"""
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        else:
            writer = csv.DictWriter(f, fieldnames=fields)
        writer.writerow(row)


# --------------------------------
# Main
# --------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("-k", "--api-key", required=True)
    parser.add_argument("-o", "--output", default="krdict_output.csv")
    parser.add_argument("-d", "--delimiter", choices=["csv", "tab"], default="tab")
    parser.add_argument("--sleep", type=float, default=2)
    parser.add_argument("--start", type=float, default=1)

    args = parser.parse_args()

    rows, fields = load_csv(args.file, args.delimiter)
    
    if not "target_code" in fields:
        fields += [
            "target_code",
            "word_grade",
            "trans_word"
            "link",
        ]
        
    if args.start == 1:
        # 最初に出力ファイルを初期化（ヘッダー書き込み）
        init_output_csv(args.output, fields, args.delimiter)

    total = 0
    hit = 0

    for index, row in enumerate(rows):
        if index < args.start - 1:
            continue

        if row.get("trans_word"):
            print(f"[{index+1}/{len(rows)}] {row['word']}, skipped.")
            append_row_to_csv(args.output, row, fields, args.delimiter)
            continue
        print(f"[{index+1}/{len(rows)}] {row['word']}")


        row["target_code"] = ""
        row["word_grade"] = ""
        row["link"] = ""
        row["trans_word"] = ""

        # has_hanja または has_hangul でない場合に検索実行
        has_hanja_def = has_hanja(row["def"])
        has_hangul_def = has_hangul(row["def"])
        base_word = strip_number(row["word"])

        if classify_puri(row["def"]) != "hangul" or base_word == row["word"]:
            total += 1

            origin = normalize_def(row["def"])
            pos_code = get_pos_code(row["pos"])
            
            use_origin_match = classify_puri(row["def"]) in ("hanja", "other")

            try:
                xml_text = search_krdict(
                    args.api_key,
                    base_word,
                    pos_code
                )

                entries = parse_entries(xml_text)

                picked = pick_entry(
                    entries,
                    base_word,
                    origin,
                    use_origin_match=use_origin_match
                )

                if picked:
                    row["target_code"] = picked["target_code"]
                    row["word_grade"] = get_word_grade(picked["word_grade"])
                    row["link"] = picked["link"]
                    if picked["trans_word"]:
                        row["trans_word"] = picked["trans_word"]
                    else:
                        row["trans_word"] = picked["trans_dfn"]
                    hit += 1

            except Exception as e:
                print("ERROR:", base_word, e)

            time.sleep(args.sleep)

        # 1行処理するごとに追記保存
        append_row_to_csv(args.output, row, fields, args.delimiter)

    print("==== 完了 ====")
    print("対象件数:", total)
    print("一致件数:", hit)
    print("出力:", args.output)


if __name__ == "__main__":
    main()