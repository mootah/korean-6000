#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KRDict View API を使って target_code から例文とフレーズを補完するスクリプト

入力CSV: target_code が存在するCSV
出力CSV: sentence, sentence_ja, examples フィールドが追加された新しいCSV

KRDICT View API エンドポイント: https://krdict.korean.go.kr/api/view
"""

import csv
import time
import argparse
import requests
import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator

VIEW_API_URL = "https://krdict.korean.go.kr/api/view"
MAX_EXAMPLES = 3
MAX_PHRASES = 5


def translate_text(text, dest='ja'):
    """韓国語テキストを日本語に翻訳"""
    if not text or not text.strip():
        return ""
    
    retry = 3
    for i in range(retry):
        try:
            result = GoogleTranslator(source='ko', target=dest).translate(text.strip())
            return result
        except Exception as e:
            print(f"  翻訳リトライ {i+1}/3: {e}")
            time.sleep(1)
    
    return ""


def fetch_word_details(api_key, target_code):
    """
    target_code を指定して KRDict View API から単語詳細を取得
    """
    params = {
        "key": api_key,
        "method": "target_code",
        "q": target_code,
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
    View API のレスポンスXMLをパースして例文とフレーズを抽出
    """
    root = ET.fromstring(xml_text)
    item = root.find(".//item")

    if item is None:
        return None

    examples = []  # 문장
    phrases = []   # 구

    # example_info ノードから type で判別
    for example_info in item.findall(".//example_info"):
        type_val = example_info.findtext("type", default="").strip()
        example_text = example_info.findtext("example", default="").strip()

        if not example_text:
            continue
        
        if type_val == "문장" and len(examples) < MAX_EXAMPLES:
            examples.append(example_text)
        elif type_val == "구" and len(phrases) < MAX_PHRASES:
            phrases.append(example_text)

    return {
        "sub": item.findtext(".//sup_no", default="").strip(),
        "examples": examples,
        "phrases": phrases
    }


def build_examples_html(examples, phrases):
    """例文とフレーズを指定されたHTML形式に整形"""
    html_parts = []

    # 例文セクション
    if examples:
        html_parts.append('<details>')
        html_parts.append('  <summary>例文</summary>')
        html_parts.append('  <ul>')
        for ko_text in examples:
            ja_text = translate_text(ko_text)
            html_parts.append('    <li>')
            html_parts.append(f'      {ko_text}')
            html_parts.append('      <blockquote>')
            html_parts.append(f'      {ja_text}')
            html_parts.append('      </blockquote>')
            html_parts.append('    </li>')
        html_parts.append('  </ul>')
        html_parts.append('</details>')

    # フレーズセクション
    if phrases:
        html_parts.append('<details>')
        html_parts.append('  <summary>フレーズ</summary>')
        html_parts.append('  <ul>')
        for ko_text in phrases:
            ja_text = translate_text(ko_text)
            html_parts.append('    <li>')
            html_parts.append(f'      {ko_text}')
            html_parts.append('      <blockquote>')
            html_parts.append(f'      {ja_text}')
            html_parts.append('      </blockquote>')
            html_parts.append('    </li>')
        html_parts.append('  </ul>')
        html_parts.append('</details>')

    return "\n".join(html_parts)


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
        description="target_code から KRDict API で例文とフレーズを補完する"
    )
    parser.add_argument("input_file", help="入力CSVファイルパス")
    parser.add_argument("-k", "--api-key", required=True, help="KRDict Open API キー")
    parser.add_argument("-o", "--output", default="krdict_examples_filled.csv", help="出力CSVファイルパス")
    parser.add_argument("-d", "--delimiter", choices=["csv", "tab"], default="tab", help="CSV区切り文字")
    parser.add_argument("--sleep", type=float, default=1.5, help="APIリクエスト間の待機時間(秒)")
    parser.add_argument("--start", type=int, default=1, help="処理開始行番号 (1から始まる)")

    args = parser.parse_args()

    rows, fields = load_csv(args.input_file, args.delimiter)

    # 新規フィールドを追加
    new_fields = fields.copy()
    for add_field in ["sentence", "sentence_ja", "examples", "sub"]:
        if add_field not in new_fields:
            new_fields.append(add_field)

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

        if row["sentence"]:
            print(f"[{line_num}/{len(rows)}] スキップ (sentenceあり): {row.get('word', '')}")
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
                    # フレーズ1件目を sentence, sentence_ja にセット
                    sentence = ""
                    sentence_ja = ""
                    if details["phrases"]:
                        sentence = details["phrases"][0]
                        details["phrases"] = details["phrases"][1:]
                    
                    if not sentence and details["examples"]:
                        sentence = details["examples"][0]
                        details["examples"] = details["examples"][1:]
                    

                    sentence_ja = translate_text(sentence)
                    
                    # HTML作成
                    examples_html = build_examples_html(details["examples"], details["phrases"])

                    # 値をセット
                    row["sub"] = details["sub"]
                    row["sentence"] = sentence
                    row["sentence_ja"] = sentence_ja
                    row["examples"] = examples_html

                    filled_count += 1
                    print(f"  ✓ 補完完了: 例文={len(details['examples'])}件 フレーズ={len(details['phrases'])}件")
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