#!/usr/bin/env python3
"""集計CSVから可視化HTMLと通知文を作る。

使い方: python3 houjin_report.py 集計.csv 出力.html 通知文.txt
出典: 国税庁法人番号公表サイト（国税庁）をもとに作成
HTMLの様式は分析基盤の共通レポートテンプレート（analysis-hub）に従う。
"""
import csv
import html as html_mod
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


def load_cross(src):
    """集計CSVと同名の _cross.csv（都道府県 × 法人種別）があれば読む。"""
    path = os.path.splitext(src)[0] + "_cross.csv"
    if not os.path.exists(path):
        return None, []
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        rows = []
        for row in r:
            d = {"prefecture": row[0], "total": int(row[-1])}
            for k, v in zip(header[1:-1], row[1:-1]):
                d[k] = int(v)
            rows.append(d)
    return rows, header[1:-1]


def load_yoy(src):
    """集計CSVと同名の _yoy.csv（法人種別 × 月の前年同月比）があれば読む。"""
    path = os.path.splitext(src)[0] + "_yoy.csv"
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[(row["designated_month"], row["entity_kind"])] = row
    return out


def fmt_pct(v):
    if v in ("", None):
        return "—"
    f = float(v)
    return "%s%.1f%%" % ("+" if f > 0 else "", f)


def main(src, html_out, notify_out):
    monthly = load(src)
    months = sorted(m for m in monthly if m >= "2015-11")[-24:]
    total_all = {k: sum(monthly[m][k] for m in months) for k in KINDS}
    last, prev = months[-1], months[-2]
    yoy = load_yoy(src)
    lines = ["【法人番号・新規指定の月次まとめ】", "対象: 直近24か月（%s〜%s）" % (months[0], last)]
    for k in KINDS:
        d = monthly[last][k] - monthly[prev][k]
        sign = "+" if d >= 0 else ""
        line = "%s: %s は %s件（前月比 %s%s件）／24か月計 %s件" % (k, last, format(monthly[last][k], ","), sign, format(d, ","), format(total_all[k], ","))
        y = yoy.get((last, k))
        if y:
            yd = int(y["yoy_diff"])
            line += "／前年同月比 %s%s件（%s）" % ("+" if yd >= 0 else "", format(yd, ","), fmt_pct(y["yoy_pct"]))
        lines.append(line)
    lines.append("出典: 国税庁法人番号公表サイト（国税庁）をもとに作成")
    notify_text = "\n".join(lines)

    chart = '<div class="chart">%s</div>' % svg_bars(monthly, months)
    note = ('<p class="note">凡例: 青=株式会社、緑=合同会社。法人番号の指定件数は、'
            '制度開始（2015年10月）以降に設立された法人については新規設立の近似として読めます。</p>')
    body = section("01", "CHART", "月次の指定件数", chart + note)

    cross, cross_kinds = load_cross(src)
    if cross:
        disp_kinds = ["株式会社", "合同会社", "有限会社", "その他の設立登記法人"]
        other_kinds = [k for k in cross_kinds if k not in disp_kinds]
        trs = []
        for r in cross[:20]:
            pref = r["prefecture"] or "（都道府県の記載なし）"
            other = sum(r.get(k, 0) for k in other_kinds)
            cells = "".join("<td>%s</td>" % format(r.get(k, 0), ",") for k in disp_kinds)
            trs.append("<tr><td>%s</td>%s<td>%s</td><td>%s</td></tr>" % (
                html_mod.escape(pref), cells, format(other, ","), format(r["total"], ",")))
        grand = {k: sum(r.get(k, 0) for r in cross) for k in cross_kinds}
        grand_other = sum(grand.get(k, 0) for k in other_kinds)
        trs.append("<tr><td>全国計</td>%s<td>%s</td><td>%s</td></tr>" % (
            "".join("<td>%s</td>" % format(grand.get(k, 0), ",") for k in disp_kinds),
            format(grand_other, ","), format(sum(grand.values()), ",")))
        cross_table = ('<div class="table-wrap"><table class="data"><thead><tr>'
                       "<th>都道府県</th><th>株式会社</th><th>合同会社</th><th>有限会社</th>"
                       "<th>その他の設立登記法人</th><th>その他</th><th>合計</th>"
                       "</tr></thead><tbody>%s</tbody></table></div>" % "".join(trs))
        cross_note = ('<p class="note">対象は直近24か月（%s〜%s）に指定された現存法人の件数です。'
                      '都道府県の合計が大きい順に上位20件と全国計を表示しています。「その他」は'
                      '国の機関・地方公共団体・合名会社・合資会社・外国会社等・その他の合算です。</p>'
                      % (months[0], last))
        body += section("02", "DATA", "都道府県 × 法人種別のクロス集計", cross_table + cross_note)

    yoy_last = [(k, yoy[(last, k)]) for k in
                sorted({k for (m, k) in yoy if m == last},
                       key=lambda k: -int(yoy[(last, k)]["count"]))]
    if yoy_last:
        trs = []
        for k, y in yoy_last:
            yd = int(y["yoy_diff"])
            trs.append("<tr><td>%s</td><td>%s件</td><td>%s件</td><td>%s%s件</td><td>%s</td></tr>" % (
                html_mod.escape(k), format(int(y["count"]), ","),
                format(int(y["prev_year_count"]), ","), "+" if yd >= 0 else "",
                format(yd, ","), fmt_pct(y["yoy_pct"])))
        yoy_table = ('<div class="table-wrap"><table class="data"><thead><tr>'
                     "<th>法人種別</th><th>%s</th><th>%s（前年同月）</th><th>増減</th><th>前年同月比</th>"
                     "</tr></thead><tbody>%s</tbody></table></div>"
                     % (last, yoy_last[0][1]["prev_year_month"], "".join(trs)))
        yoy_note = ('<p class="note">最新月（%s）は公表時点までの指定分です。'
                    '前年同月と母数を揃えた比較として読んでください。</p>' % last)
        body += section("03", "DATA", "前年同月比（最新月・法人種別）", yoy_table + yoy_note)

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
