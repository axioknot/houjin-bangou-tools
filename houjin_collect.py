#!/usr/bin/env python3
"""国税庁 法人番号公表サイトの全件データ（全国・CSV Unicode）を取得する。

取得は公表サイトの通常のダウンロード手順（フォーム送信）を再現する。
データの利用条件は公共データ利用規約（第1.0版）に準拠する。
利用時は出典の記載と、編集・加工した旨の記載が必要。

使い方: python3 houjin_collect.py [出力先ディレクトリ]
"""
import http.cookiejar
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://www.houjin-bangou.nta.go.jp"
PAGE = BASE + "/pc/download/zenken/index.html"


def fetch_zenkoku_unicode(out_dir):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", "houjin-bangou-collect/0.1 (public data accumulation; contact: accounts@axioknot.com)")]
    html = op.open(PAGE, timeout=60).read().decode("utf-8", "ignore")

    # CSV Unicode セクションの最初のダウンロードリンクが「全国」
    sec = html.find('id="csv-unicode"')
    if sec < 0:
        raise RuntimeError("csv-unicode section not found")
    m = re.search(r"doDownload\((\d+)\)", html[sec:])
    if not m:
        raise RuntimeError("download link not found in csv-unicode section")
    file_no = m.group(1)

    token = re.search(r'CNSFWTokenProcessor\.request\.token" value="([^"]+)"', html).group(1)
    data = urllib.parse.urlencode({
        "jp.go.nta.houjin_bangou.framework.web.common.CNSFWTokenProcessor.request.token": token,
        "event": "download",
        "selDlFileNo": file_no,
    }).encode()
    req = urllib.request.Request(BASE + "/download/zenken/index.html", data=data)

    date_m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日更新", html[sec - 2000:sec + 2000])
    stamp = "unknown"
    if date_m:
        stamp = f"{int(date_m.group(1)):04d}{int(date_m.group(2)):02d}{int(date_m.group(3)):02d}"
    out = os.path.join(out_dir, f"zenkoku_unicode_{stamp}.zip")
    n = 0
    with op.open(req, timeout=300) as r, open(out, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
    print(f"saved {n} bytes -> {out}")
    return out


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out_dir, exist_ok=True)
    fetch_zenkoku_unicode(out_dir)
