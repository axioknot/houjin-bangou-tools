# houjin-bangou-tools

国税庁「法人番号公表サイト」の全件データ（全国・CSV Unicode）を取得して、都道府県 × 法人種別 × 法人番号指定年月の件数に集計し、月次のグラフと通知文を作る道具です。Python の標準ライブラリだけで動きます。

## ファイル

- `houjin_collect.py`：公表サイトのダウンロードフォームの手順で、全件データの zip を取得します。ファイル名には公表サイトの更新日が入ります（例: `zenkoku_unicode_20261030.zip`）
- `houjin_aggregate.py`：zip を展開した全件CSVから、現存法人の件数を都道府県・法人種別・指定年月ごとに集計してCSVに出力します。最新履歴でない行と、閉鎖済みの法人は除きます
- `houjin_report.py`：集計CSVから、直近24か月の株式会社と合同会社の件数を積み上げ棒グラフにしたHTMLと、最新月の件数と前月比を書いた通知文を作ります。環境変数 `DISCORD_WEBHOOK_URL` が設定されていれば、通知文を Discord にも送ります

## 使い方

```sh
# 1. 全件データをダウンロードする（zip は、2026年10月30日更新分で約256MBあります）
python3 houjin_collect.py data/

# 2. data/ の zip を展開し、全件CSVを集計する
#    ファイル名は分割されていない場合の形です（分割されている場合は末尾に連番が付きます）
#    日付の部分は、手元のファイルに合わせてください
python3 houjin_aggregate.py data/00_zenkoku_all_20261030.csv houjin_monthly_formations.csv

# 3. グラフと通知文を作る
python3 houjin_report.py houjin_monthly_formations.csv houjin_report.html houjin_notify.txt
```

## 集計の読み方

列の定義は、国税庁の「リソース定義書（ダウンロードファイル、Web-API）」に基づきます。

この集計では、制度が始まった2015年10月5日より後に新規に設立登記された法人については、法人番号の指定年月を設立時期の近似として扱います。指定は、法務省から提供を受けた登記情報に基づいて行われます。それより前からある設立登記法人は、2015年10月5日にまとめて指定されているので、設立時期としては読めません。設立登記のない法人等は届出に基づいて指定されるため、この読み方は当てはまりません。

## データの出典

国税庁法人番号公表サイト（国税庁）（https://www.houjin-bangou.nta.go.jp/pc/download/zenken/index.html）をもとに作成。

データの利用条件は、公共データ利用規約（第1.0版）に準拠します。利用の際は出典の記載が必要です。編集・加工して利用する場合は、その旨も記載してください。

## ライセンス

MIT License です。詳しくは LICENSE を見てください。
