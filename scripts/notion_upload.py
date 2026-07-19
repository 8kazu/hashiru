#!/usr/bin/env python3
"""HTMLレポートをNotionページにアップロードする。

usage: python3 scripts/notion_upload.py <report.html> [summary.md]

.env（リポジトリルート）に以下を設定:
  NOTION_TOKEN=ntn_xxx        # Notion内部インテグレーションのトークン
  NOTION_PAGE_ID=xxxx         # 追記先ページのID（ページURLをそのまま貼ってもOK）

動作:
  1. summary.md をNotionブロック（見出し・箇条書き）に変換してページ本文に追記
  2. HTMLファイルをNotion File Upload APIでアップロードし、fileブロックとして添付
標準ライブラリのみ使用（requests不要）。
"""
import json
import re
import sys
import uuid
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict:
    env = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def normalize_page_id(raw: str) -> str:
    """ページURL/ID文字列から32桁hexのページIDを取り出す。"""
    raw = raw.lower()
    # ダッシュ付きUUID形式を優先
    dashed = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", raw)
    if dashed:
        return dashed[-1].replace("-", "")
    # NotionのURL末尾は32桁hexが連続する（前後に区切りがある）
    matches = re.findall(r"(?<![0-9a-z])[0-9a-f]{32}(?![0-9a-z])", raw)
    if not matches:
        matches = re.findall(r"[0-9a-f]{32}", raw)
    if not matches:
        sys.exit(f"NOTION_PAGE_ID からページIDを抽出できません: {raw}")
    return matches[-1]


def api_request(method: str, path: str, token: str, payload=None, raw_body=None, content_type="application/json"):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
    }
    data = None
    if raw_body is not None:
        data = raw_body
        headers["Content-Type"] = content_type
    elif payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"Notion APIエラー {e.code} ({method} {path}):\n{body}")


def upload_file(html_path: Path, token: str) -> str:
    """File Upload APIでHTMLをアップロードし、file_upload IDを返す。"""
    created = api_request("POST", "/file_uploads", token, payload={
        "filename": html_path.name,
        "content_type": "text/html",
    })
    upload_id = created["id"]

    boundary = uuid.uuid4().hex
    content = html_path.read_bytes()
    if len(content) > 20 * 1024 * 1024:
        sys.exit("ファイルが20MBを超えています（single-part上限）")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{html_path.name}"\r\n'
        f"Content-Type: text/html\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    api_request(
        "POST", f"/file_uploads/{upload_id}/send", token,
        raw_body=body, content_type=f"multipart/form-data; boundary={boundary}",
    )
    return upload_id


def rich_text(text: str) -> list:
    return [{"type": "text", "text": {"content": text[:2000]}}]


def markdown_to_blocks(md: str) -> list:
    """要約Markdownを簡易的にNotionブロックへ変換する。"""
    blocks = []
    for line in md.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": rich_text(line[4:])}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": rich_text(line[3:])}})
        elif line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": rich_text(line[2:])}})
        elif line.lstrip().startswith(("- ", "* ")):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": rich_text(line.lstrip()[2:])}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": rich_text(line)}})
    return blocks[:90]  # 1リクエスト100ブロック上限に余裕を持たせる


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    html_path = Path(sys.argv[1])
    if not html_path.is_absolute():
        html_path = ROOT / html_path
    if not html_path.exists():
        sys.exit(f"ファイルが見つかりません: {html_path}")
    summary_path = None
    if len(sys.argv) >= 3:
        summary_path = Path(sys.argv[2])
        if not summary_path.is_absolute():
            summary_path = ROOT / summary_path

    env = load_env()
    token = env.get("NOTION_TOKEN")
    page_raw = env.get("NOTION_PAGE_ID")
    if not token or not page_raw:
        sys.exit(".env に NOTION_TOKEN と NOTION_PAGE_ID を設定してください")
    page_id = normalize_page_id(page_raw)

    # レポート名（例: 2026-07-11_morning.html → 2026-07-11 朝版）
    stem = html_path.stem
    edition_ja = {"morning": "朝版", "evening": "夜版", "adhoc": "随時版"}
    label = stem
    m = re.match(r"(\d{4}-\d{2}-\d{2})_(\w+)", stem)
    if m:
        label = f"{m.group(1)} {edition_ja.get(m.group(2), m.group(2))}"

    # 1. ファイルアップロード
    upload_id = upload_file(html_path, token)

    # 2. ブロック組み立て: 見出し → 添付 → 本文要約 → 区切り線
    children = [
        {"object": "block", "type": "heading_1",
         "heading_1": {"rich_text": rich_text(f"📰 {label}")}},
        {"object": "block", "type": "file",
         "file": {"type": "file_upload", "file_upload": {"id": upload_id},
                  "name": html_path.name}},
    ]
    if summary_path and summary_path.exists():
        children += markdown_to_blocks(summary_path.read_text(encoding="utf-8"))
    children.append({"object": "block", "type": "divider", "divider": {}})

    api_request("PATCH", f"/blocks/{page_id}/children", token, payload={"children": children})
    print(f"OK: {html_path.name} をNotionページに追記しました")


if __name__ == "__main__":
    main()
