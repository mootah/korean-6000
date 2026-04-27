#!/usr/bin/env python3
import csv
import re
import sys

def format_examples_html(html: str) -> str:
    """
    崩れたHTMLの改行とインデントを復元する
    """
    # 連続する空白を正規化
    html = re.sub(r'\s+', ' ', html).strip()
    
    # ブロックタグの前で改行 + インデント
    block_tags = [
        (r'<details>', 0),
        (r'<ul>', 2),
        (r'<li>', 4),
        (r'</li>', 4),
        (r'</ul>', 2),
        (r'</details>', 0),
    ]
    
    for tag, indent in block_tags:
        html = re.sub(re.escape(tag), '\n' + (' ' * indent) + tag, html)
    
    # <li> 内のテキストの前で改行
    html = re.sub(r'(<li>)\s*', r'\1\n' + (' ' * 6), html)
    
    # <blockquote> はタグの前で改行、同じ行にテキスト
    html = re.sub(r'<blockquote>', '\n' + (' ' * 6) + '<blockquote>', html)
    # html = re.sub(r'</blockquote>', '\n' + (' ' * 6) + '</blockquote>', html)
    
    # <summary> はタグの前で改行、同じ行にテキスト
    html = re.sub(r'<summary>', '\n' + (' ' * 2) + '<summary>', html)
    html = re.sub(r'</summary>', '</summary>', html)
    
    # 先頭の不要な改行を削除
    html = html.lstrip('\n')
    
    return html

def main():
    input_file = 'korean6000_v2.tsv'
    output_file = 'korean6000_v3.tsv'
    
    print(f'Processing {input_file} ...')
    
    with open(input_file, 'r', encoding='utf-8', newline='') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.DictReader(infile, delimiter='\t')
        fields = list(reader.fieldnames or [])
        writer = csv.DictWriter(outfile, fieldnames=fields, delimiter='\t', lineterminator='\n')
        
        writer.writeheader()
        
        count = 0
        for row in reader:
            if row['examples']:
                row['examples'] = format_examples_html(row['examples'])
            writer.writerow(row)
            count += 1
            
            if count % 1000 == 0:
                print(f'Processed {count} rows...')
    
    print(f'Done. Total {count} rows processed.')
    print(f'Output saved to {output_file}')

if __name__ == '__main__':
    main()