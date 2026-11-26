#!/usr/bin/env python3
"""集計CSVから可視化HTMLと通知文を作る。

使い方: python3 houjin_report.py 集計.csv 出力.html 通知文.txt
出典: 国税庁法人番号公表サイト（国税庁）をもとに作成
HTMLの様式は分析基盤の共通レポートテンプレート（analysis-hub）に従う。
"""
import csv
import json
import os
import sys
import urllib.request
from collections import defaultdict

KINDS = ["株式会社", "合同会社"]


def load(path):
    monthly = defaultdict(lambda: defaultdict(int))
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            monthly[row["designated_month"]][row["entity_kind"]] += int(row["count"])
    return monthly


def svg_bars(monthly, months):
    w, h, pad = 960, 320, 44
    top = max((sum(monthly[m][k] for k in KINDS) for m in months), default=1)
    bw = (w - pad * 2) / max(len(months), 1)
    parts = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img">' % (w, h)]
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#B9B6AB"/>' % (pad, h - pad, w - pad, h - pad))
    colors = {"株式会社": "#3b6ea5", "合同会社": "#7fb069"}
    for i, m in enumerate(months):
        x = pad + i * bw
        y0 = h - pad
        for k in KINDS:
            v = monthly[m][k]
            bh = (h - pad * 2) * v / top
            y0 -= bh
            parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"><title>%s %s: %s件</title></rect>' % (x + 1, y0, bw - 2, bh, colors[k], m, k, format(v, ",")))
        if i % 3 == 0:
            parts.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle" fill="#55534E">%s</text>' % (x + bw / 2, h - pad + 16, m[2:]))
    parts.append("</svg>")
    return "".join(parts)


def render_page(title, kicker, h1, lede, body, foot):
    """共通レポートテンプレート（analysis-hub）でページを組み立てる。

    テンプレートが見つからない環境（パーツ単体での利用）では、
    最小限の埋め込み様式にフォールバックする。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    tpl_path = os.path.join(here, "..", "analysis-hub", "report_template.html")
    try:
        with open(tpl_path, encoding="utf-8") as f:
            tpl = f.read()
    except OSError:
        tpl = None
    if tpl is None:
        return ("<!DOCTYPE html>\n<html lang=\"ja\"><head><meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                "<title>%s</title></head><body><h1>%s</h1>%s%s<footer>%s</footer></body></html>"
                % (title, h1, lede, body, foot))
    page = tpl
    for key, val in (("{{TITLE}}", title), ("{{KICKER}}", kicker), ("{{H1}}", h1),
                     ("{{LEDE}}", lede), ("{{BODY}}", body), ("{{FOOT}}", foot)):
        page = page.replace(key, val)
    return page


def section(no, label, title, inner):
    return ('<section class="sec"><div class="sec-head">'
            '<span class="sec-no">%s</span><span class="sec-label">%s</span><h2>%s</h2>'
            '</div>%s</section>' % (no, label, title, inner))


def main(src, html_out, notify_out):
    monthly = load(src)
    months = sorted(m for m in monthly if m >= "2015-11")[-24:]
    total_all = {k: sum(monthly[m][k] for m in months) for k in KINDS}
    last, prev = months[-1], months[-2]
    lines = ["【法人番号・新規指定の月次まとめ】", "対象: 直近24か月（%s〜%s）" % (months[0], last)]
    for k in KINDS:
        d = monthly[last][k] - monthly[prev][k]
        sign = "+" if d >= 0 else ""
        lines.append("%s: %s は %s件（前月比 %s%s件）／24か月計 %s件" % (k, last, format(monthly[last][k], ","), sign, format(d, ","), format(total_all[k], ",")))
    lines.append("出典: 国税庁法人番号公表サイト（国税庁）をもとに作成")
    notify_text = "\n".join(lines)

    chart = '<div class="chart">%s</div>' % svg_bars(monthly, months)
    note = ('<p class="note">凡例: 青=株式会社、緑=合同会社。法人番号の指定件数は、'
            '制度開始（2015年10月）以降に設立された法人については新規設立の近似として読めます。</p>')
    body = section("01", "CHART", "月次の指定件数", chart + note)
    foot = "<p>出典: 国税庁法人番号公表サイト（国税庁）をもとに作成</p>"
    html = render_page("新規法人の指定件数（月次）", "CORPORATE NUMBER / MONTHLY",
                       "新規法人の指定件数（月次）— 株式会社と合同会社", "", body, foot)
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)
    with open(notify_out, "w", encoding="utf-8") as f:
        f.write(notify_text + "\n")
    print(notify_text)

    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if url:
        req = urllib.request.Request(url, data=json.dumps({"content": notify_text}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "houjin-bangou-tools/0.1"})
        urllib.request.urlopen(req, timeout=30)
        print("notified: discord webhook")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
