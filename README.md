# hashiru — デイリーニュースレポート

毎日のニュース（AI・テック / 経済 / 脳神経科学 / サッカー / Xバズ）をHTMLレポートとして生成し、Notionにも掲載するツール。仕様は `spec/spec.md` を参照。

## 使い方

```bash
cd ~/hashiru
./hashiru morning   # 朝版（海外中心）を生成
./hashiru evening   # 夜版（国内中心）を生成
```

生成物: `reports/YYYY-MM-DD_{morning|evening}.html`（＋Notion用要約 `.summary.md`）。生成後、`.env` があればNotionへ自動アップロードし、ブラウザで自動的に開く。

どこからでも実行したい場合はエイリアスを追加:

```bash
echo 'alias hashiru="$HOME/hashiru/hashiru"' >> ~/.zshrc && source ~/.zshrc
hashiru morning
```

## 初回セットアップ

1. **実行権限**（設定済みのはず。動かなければ）: `chmod +x ~/hashiru/hashiru`
2. **Claude Code CLI**: `claude --version` で確認。生成は `claude -p`（ヘッドレス）で行う。
3. **Notion連携**:
   1. https://www.notion.so/my-integrations で「内部インテグレーション」を作成しトークンを取得
   2. レポートを溜めたいNotionページを開き、右上「…」→「コネクト」で作成したインテグレーションを接続
   3. `cp .env.example .env` して `NOTION_TOKEN` と `NOTION_PAGE_ID`（ページURLをそのまま貼ってOK）を設定

`.env` が無い場合、Notionアップロードはスキップされる（レポート生成は動く）。

## 定時実行（launchd — 推奨）

Claudeアプリを開いていなくても動く。スリープで実行時刻を逃しても**復帰時に自動実行**される（cronはスキップされる）。

```bash
cd ~/hashiru
./scripts/install_launchd.sh            # 朝7:00・夜22:00 のエージェントを登録
launchctl list | grep hashiru           # 登録確認
launchctl kickstart gui/$(id -u)/com.hashiru.morning   # 手動テスト実行
tail -f reports/launchd.log             # ログ確認
./scripts/install_launchd.sh uninstall  # 解除
```

- plist本体は `launchd/` にあり、時刻を変えたい場合はplistの `Hour`/`Minute` を編集して再インストール
- 定時実行時はブラウザ自動オープンをスキップ（`HASHIRU_NO_OPEN=1`）
- Macの電源が完全に切れている間の回は実行されない（スリープはOK）

### 代替: cron（Macを常時起動している場合）

```cron
0 7 * * *  $HOME/hashiru/hashiru morning >> $HOME/hashiru/reports/cron.log 2>&1
0 22 * * * $HOME/hashiru/hashiru evening >> $HOME/hashiru/reports/cron.log 2>&1
```

※ Claude（Cowork）側のスケジュールタスク（朝7時・夜22時）も登録済み。ただしCowork側はサンドボックスのネットワーク制限によりNotionアップロードは行われない（HTML生成のみ）。launchdに一本化するならCowork側タスクは削除を推奨。

## 株ウォッチリスト

`watchlist.json` で管理。Claudeとのチャットで「〇〇を買った / 売った」と伝えれば更新される。手動編集も可:

```json
{ "stocks": [ { "ticker": "NVDA", "name": "NVIDIA", "market": "US", "added": "2026-07-11", "note": "保有" } ] }
```

## 構成

```
hashiru                     # CLIエントリポイント
prompts/{morning,evening}.md   # レポート生成プロンプト
scripts/notion_upload.py       # Notionアップロード（標準ライブラリのみ）
scripts/install_launchd.sh     # launchd登録/解除
launchd/*.plist          # launchdエージェント定義（朝7時・夜22時）
watchlist.json           # 株ウォッチリスト
reports/                 # 生成されたレポート
spec/spec.md             # 仕様書
.env                     # Notion認証情報（git管理外にすること）
```
