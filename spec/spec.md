# hashiru — デイリーニュースレポート 仕様書

- 作成日: 2026-07-11
- 更新日: 2026-07-11（v1.1: ターミナルCLI・Notion連携を追加）
- ステータス: v1.1（確定）

## 1. 概要

毎日定時（朝・夜の2回）および任意のチャット指示で、複数分野のニュースとXのバズトピックをまとめたレポートをHTML形式で生成するツール。

## 2. ユーザープロファイル

エンジニア。AI、株式（国内・外国）、経済に強い関心。脳神経科学を中心とするアカデミック領域にも高い関心。サッカーもフォロー（特定クラブのこだわりなし）。

## 3. トピック構成

1. **今日の一本** — 全分野から最重要ニュース1つを冒頭に
2. **AI・テック** — モデル/研究リリース（OpenAI/Anthropic/Google/Meta/中国勢）、開発者向けニュース（エージェント、コーディング支援、フレームワーク）、半導体・インフラ（NVIDIA、TSMC、データセンター）、規制・政策
3. **最先端テック（AI以外）** — 量子コンピュータ、ロボティクス、宇宙、バイオテック、ビッグテックのプロダクト・経営動向
4. **マーケット・経済** — 米国市況（指数、金利、FRB）、日本市況（日経、日銀）、為替（ドル円）、マクロ指標（CPI、雇用統計）、ウォッチリスト銘柄の株価・決算・材料
5. **脳神経科学・アカデミア** — 主要誌の注目論文（Nature Neuroscience、Neuron、Science系）、BCI（Neuralink等）、AI×神経科学の交差領域、arXivトレンド（cs.AI / q-bio.NC）、研究資金・科学政策
6. **サッカー** — 主要リーグ（プレミア、ラ・リーガ、セリエA、ブンデス、J1）の結果・順位、移籍情報、日本代表・海外組
7. **Xバズトピック** — 各分野でエンジニア・研究者界隈が話題にしているもの、分野横断のバズ

## 4. 株ウォッチリスト（動的管理）

- `~/hashiru/watchlist.json` で銘柄を管理。レポート生成時に毎回読み込む
- チャットで「〇〇を買った / 売った」と伝えるだけでClaudeが追加・削除
- 国内株・外国株の両方に対応
- スキーマ:

```json
{
  "stocks": [
    {
      "ticker": "NVDA",
      "name": "NVIDIA",
      "market": "US",
      "added": "2026-07-11",
      "note": "保有"
    }
  ]
}
```

- `market`: "US" | "JP" | その他市場コード
- `note`: 任意（保有/監視のみ、購入理由など）

## 5. レポート形式

- **出力**: HTML 1ファイル（self-contained、ブラウザで閲覧）
- **保存先**: `~/hashiru/reports/YYYY-MM-DD_{morning|evening|adhoc}.html`
- **二層構造**: 各ニュースは「サッと読める要約（2〜3文）」を常時表示し、クリックで「深掘り（背景・影響・関連情報）」を展開（`<details>` 等）
- **出典**: 各ニュースに出典リンクを付ける
- **言語**: 日本語

## 6. 実行方法

### 定時実行（スケジュールタスク2本）

| タスク | 時刻 | 重点 |
|---|---|---|
| morning-news-report | 毎日 7:00 | 海外中心: 一晩の米国市況、海外テック・AIニュース、欧州サッカーの結果 |
| evening-news-report | 毎日 22:00 | 国内中心: 日本市況の結果、国内ニュース、その日のバズトピック |

- 注意: スケジュールタスクはClaudeアプリ起動中に実行される。閉じていた場合は次回起動時に実行される。

### 随時実行

チャットで「レポート作って」等と指示すればその場で生成（adhoc）。

### ターミナル実行（hashiru コマンド）

```bash
~/hashiru/hashiru morning   # 朝版
~/hashiru/hashiru evening   # 夜版
```

- Claude Code CLI（`claude -p`、ヘッドレス）で `prompts/{edition}.md` を実行
- HTML＋Notion用要約Markdown（`.summary.md`）を生成 → Notionアップロード → ブラウザで開く
- cronに登録すればClaudeアプリを開かずに定時実行可能（README参照）
- 注意: Cowork側スケジュールタスクはサンドボックスのネットワーク制限によりNotionアップロード不可（HTML生成のみ）

## 7. Notion連携

- 生成のたびに、指定Notionページへ以下を追記する（スマホ閲覧用）:
  1. 見出し（例: 📰 2026-07-11 朝版）
  2. HTMLファイル添付（Notion File Upload API、20MB以下のsingle-part）
  3. 本文要約（`.summary.md` を見出し・箇条書きブロックに変換、最大90ブロック）
  4. 区切り線
- 実装: `scripts/notion_upload.py`（Python標準ライブラリのみ、Notion-Version 2022-06-28）
- 認証: `~/hashiru/.env` の `NOTION_TOKEN`（内部インテグレーション）と `NOTION_PAGE_ID`（ページURL可）
- 前提: 対象ページの「コネクト」でインテグレーションを接続しておくこと

## 8. ディレクトリ構成

```
~/hashiru/
├── hashiru                 # ターミナル用CLI（bash）
├── prompts/
│   ├── morning.md       # 朝版プロンプト
│   └── evening.md       # 夜版プロンプト
├── scripts/
│   └── notion_upload.py # Notionアップロード
├── spec/
│   └── spec.md          # 本仕様書
├── watchlist.json       # 株ウォッチリスト
├── .env                 # Notion認証情報（.env.example参照）
├── README.md            # セットアップ・使い方
└── reports/             # 生成されたHTMLレポート＋要約
    ├── YYYY-MM-DD_{morning|evening|adhoc}.html
    └── YYYY-MM-DD_{morning|evening|adhoc}.summary.md
```

## 9. 将来の拡張候補（未実装）

- 仮想通貨・ビットコイン欄
- 国内スタートアップ動向欄
- サッカーの特定クラブ指定
- レポートのアーカイブ一覧ページ（index.html）
