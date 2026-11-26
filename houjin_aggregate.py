#!/usr/bin/env python3
"""法人番号 全件CSV から「都道府県 × 法人種別 × 指定年月」の件数を集計する。

列の定義は国税庁「リソース定義書（ダウンロードファイル、Web-API）」に基づく:
  3列目=処理区分, 9列目=法人種別, 10列目=都道府県, 19列目=登記記録の閉鎖等年月日,
  23列目=法人番号指定年月日, 24列目=最新履歴（1=最新）
閉鎖済み（19列目に日付）は除く。指定年月日は、制度開始（2015-10-05）以降に
設立された法人については設立時期の近似として使える（それ以前の法人は
2015-10-05 に一括指定されているため、設立時期としては読めない）。

使い方: python3 houjin_aggregate.py 入力.csv 出力.csv
出典: 国税庁法人番号公表サイト（国税庁）をもとに作成
"""
import csv
import sys
from collections import Counter

KIND_NAMES = {
    "101": "国の機関",
    "201": "地方公共団体",
    "301": "株式会社",
    "302": "有限会社",
    "303": "合名会社",
    "304": "合資会社",
    "305": "合同会社",
    "399": "その他の設立登記法人",
    "401": "外国会社等",
    "499": "その他",
}


def main(src, dst):
    counts = Counter()
    total = active = 0
    with open(src, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            total += 1
            if len(row) < 30:
                continue
            if row[24 - 1] != "1":  # 最新履歴でない行は除く
                continue
            if row[19 - 1]:  # 閉鎖済みは除く
                continue
            active += 1
            pref = row[10 - 1]
            kind = KIND_NAMES.get(row[9 - 1], row[9 - 1])
            designated = row[23 - 1]  # 法人番号指定年月日
            month = designated[:7] if len(designated) >= 7 else "unknown"
            counts[(pref, kind, month)] += 1
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["prefecture", "entity_kind", "designated_month", "count"])
        for (pref, kind, month), n in sorted(counts.items()):
            w.writerow([pref, kind, month, n])
    print(f"total rows: {total}, active (latest, not closed): {active}, groups: {len(counts)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
