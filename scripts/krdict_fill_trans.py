#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KRDict View API を使って target_code から不足情報を補完するスクリプト

入力CSV: target_code が存在し、trans_word が空のレコードがあるCSV
出力CSV: word_grade, trans_word, link が補完された新しいCSV

KRDICT View API エンドポイント: https://krdict.korean.go.kr/api/view
このAPIは target_code を直接指定して単語の詳細を取得できます
"""

import csv
import time
import argparse
import requests
import xml.etree.ElementTree as ET

VIEW_API_URL = "https://krdict.korean.go.kr/api/view"

WORD_GRADE = {
    "초급": "初級",
    "중급": "中級",
    "고급": "上級",
}


def get_word_grade(word_grade):
    return WORD_GRADE.get((word_grade or "").strip(), "")


def fetch_word_details(api_key, target_code):
    """
    target_code を指定して KRDict View API から単語詳細を取得
    """
    params = {
        "key": api_key,
        "method": "target_code",
        "q": target_code,
        "translated": "y",
        "trans_lang": 2,  # 日本語
    }

    retry = 3
    for i in range(retry):
        try:
            r = requests.get(VIEW_API_URL, params=params, timeout=20)
            r.raise_for_status()
            return r.text

        except requests.exceptions.RequestException as e:
            print(f"  リトライ {i+1}/3 target_code={target_code}: {e}")
            time.sleep(3)

    return None


def parse_view_response(xml_text):
    """
    View API のレスポンスXMLをパースして必要な情報を抽出
    """
    root = ET.fromstring(xml_text)
    item = root.find(".//item")

    if item is None:
        return None

    result = {
        "word_grade": get_word_grade(item.findtext(".//word_grade", default="")),
        # "link": item.findtext(".//link", default="").strip(),
        "trans_word": item.findtext(".//trans_word", default="（対訳なし）").strip(),
        "trans_dfn":  item.findtext(".//trans_dfn", default="").strip(),
    }

    return result


def load_csv(path, delimiter):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        if delimiter == "tab":
            reader = csv.DictReader(f, delimiter="\t")
        else:
            reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def init_output_csv(path, fields, delimiter):
    """出力CSVを初期化（ヘッダーのみ書き込み）"""
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


def main():
    parser = argparse.ArgumentParser(
        description="target_code から KRDict API で trans_word, word_grade, link を補完する"
    )
    parser.add_argument("input_file", help="入力CSVファイルパス")
    parser.add_argument("-k", "--api-key", required=True, help="KRDict Open API キー")
    parser.add_argument("-o", "--output", default="krdict_filled.csv", help="出力CSVファイルパス")
    parser.add_argument("-d", "--delimiter", choices=["csv", "tab"], default="tab", help="CSV区切り文字")
    parser.add_argument("--sleep", type=float, default=1.5, help="APIリクエスト間の待機時間(秒)")
    parser.add_argument("--start", type=int, default=1, help="処理開始行番号 (1から始まる)")

    args = parser.parse_args()

    rows, fields = load_csv(args.input_file, args.delimiter)

    new_fields = [
        "rank",
        "word",
        "pos",
        "pos_name",
        "pos_ja",
        "def",
        "level",
        "target_code",
        "word_grade",
        "trans_word",
        "trans_dfn",
        "link"
    ]

    if args.start == 1:
        init_output_csv(args.output, new_fields, args.delimiter)

    total_count = 0
    filled_count = 0

    print(f"合計 {len(rows)} 行を読み込みました")
    print(f"処理開始行: {args.start}")
    print("=" * 50)

    for index, row in enumerate(rows):
        line_num = index + 1

        if line_num < args.start:
            append_row_to_csv(args.output, row, new_fields, args.delimiter)
            continue

        # 既に trans_word が埋まっている場合はスキップ
        if row.get("trans_word") and row["trans_word"].strip():
        # if False:
            print(f"[{line_num}/{len(rows)}] スキップ (既に翻訳あり): {row.get('word', '')}")
            append_row_to_csv(args.output, row, new_fields, args.delimiter)
            continue

        target_code = row.get("target_code", "").strip()

        if not target_code or target_code == "-":
            print(f"[{line_num}/{len(rows)}] スキップ (target_codeなし): {row.get('word', '')}")
            append_row_to_csv(args.output, row, new_fields, args.delimiter)
            continue

        total_count += 1
        print(f"[{line_num}/{len(rows)}] 処理中: target_code={target_code}")

        try:
            xml_text = fetch_word_details(args.api_key, target_code)

            if xml_text:
                details = parse_view_response(xml_text)

                if details:
                    # 値を上書き
                    row["word_grade"] = details["word_grade"]
                    row["trans_word"] = details["trans_word"]
                    row["trans_dfn"] = details["trans_dfn"]
                    row["link"] = f"https://krdict.korean.go.kr/jpn/dicSearch/SearchView?ParaWordNo={target_code}"

                    filled_count += 1
                    print(f"  ✓ 補完完了: {details['trans_word']}")
                else:
                    print(f"  ✗ データが見つかりませんでした")

        except Exception as e:
            print(f"  ✗ エラー発生: {e}")

        # 処理済み行を追記保存（途中で中断してもデータが残る）
        append_row_to_csv(args.output, row, new_fields, args.delimiter)

        time.sleep(args.sleep)

    print("\n" + "=" * 50)
    print("✅ 処理完了")
    print(f"  対象件数: {total_count}")
    print(f"  補完成功: {filled_count}")
    print(f"  出力ファイル: {args.output}")


if __name__ == "__main__":
    main()