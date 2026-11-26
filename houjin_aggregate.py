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
import os
import sys
from collections import Counter, defaultdict

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

    stem = os.path.splitext(dst)[0]

    # 追加集計1: 都道府県 × 法人種別のクロス集計。
    # 対象期間はレポートの表示範囲と揃え、2015-11 以降の直近24か月とする
    # （2015-10 は制度開始時の一括指定のため、月次の読みには使わない）。
    months_all = sorted({m for (_, _, m) in counts if m >= "2015-11"})
    window = set(months_all[-24:])
    cross = Counter()
    for (pref, kind, month), n in counts.items():
        if month in window:
            cross[(pref, kind)] += n
    kinds = sorted({k for (_, k) in cross})
    pref_totals = Counter()
    for (pref, _), n in cross.items():
        pref_totals[pref] += n
    cross_path = stem + "_cross.csv"
    with open(cross_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["prefecture"] + kinds + ["total"])
        for pref, tot in pref_totals.most_common():
            w.writerow([pref] + [cross.get((pref, k), 0) for k in kinds] + [tot])
    print(f"cross: {cross_path} (window: {min(window)}..{max(window)}, prefectures: {len(pref_totals)})")

    # 追加集計2: 法人種別 × 月の前年同月比。
    monthly_kind = defaultdict(int)
    for (_, kind, month), n in counts.items():
        monthly_kind[(kind, month)] += n
    yoy_path = stem + "_yoy.csv"
    yoy_rows = 0
    with open(yoy_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["designated_month", "entity_kind", "count",
                    "prev_year_month", "prev_year_count", "yoy_diff", "yoy_pct"])
        for month in months_all:
            if month < "2016-11":
                continue
            prev_month = "%04d-%s" % (int(month[:4]) - 1, month[5:7])
            for kind in kinds:
                cur = monthly_kind.get((kind, month), 0)
                prev = monthly_kind.get((kind, prev_month), 0)
                if cur == 0 and prev == 0:
                    continue
                pct = round((cur - prev) / prev * 100, 1) if prev else ""
                w.writerow([month, kind, cur, prev_month, prev, cur - prev, pct])
                yoy_rows += 1
    print(f"yoy: {yoy_path} (rows: {yoy_rows})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
