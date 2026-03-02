# baseball-scorebook-analyzer

日本の野球スコアブック画像をドラッグ&ドロップで解析するローカルWebアプリ。
Claude Vision API を使ってスコアブックの記号・文字を解読し、構造化JSONとして出力します。

## セットアップ

### 1. リポジトリをクローン

```bash
git clone <this-repo>
cd baseball-scorebook-analyzer
```

### 2. バックエンドのセットアップ

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. APIキーの設定

```bash
cp .env.example .env
# .env を開いて ANTHROPIC_API_KEY を設定
```

### 4. バックエンドを起動

```bash
uvicorn main:app --reload --port 8000
```

動作確認: http://localhost:8000/health → `{"status":"ok"}` が返れば OK

Swagger UI: http://localhost:8000/docs

### 5. フロントエンドを起動

別のターミナルで:

```bash
cd frontend
python -m http.server 3000
```

ブラウザで http://localhost:3000 を開く

## 使い方

1. スコアブック画像（JPEG / PNG / WEBP）をドロップゾーンにドラッグ&ドロップ
2. 「解析する」ボタンをクリック
3. Claude Vision が解析し、以下を表示:
   - 試合情報（チーム名・日付・会場）
   - イニング別スコア表
   - 打者成績表（各イニングの結果コード）
   - 投手成績表
   - 解析メタデータ（信頼度・警告）

## ファイル構成

```
baseball-scorebook-analyzer/
├── backend/
│   ├── main.py           # FastAPI アプリ
│   ├── analyzer.py       # Claude Vision API 呼び出し
│   ├── schemas.py        # Pydantic データモデル
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## 将来の拡張計画

- `analyzer.py` の `analyze_scorebook_image()` 関数が唯一のモデル差し替えポイント
- `raw_claude_response` フィールドでラベル付きコーパスを自動蓄積 → ファインチューニング用
- `USE_LOCAL_MODEL=true` 環境変数でローカルモデルへの切り替えが可能（実装予定）
- `metadata.confidence` が `low` の結果をヒューマンレビューキューに送る仕組みを追加予定
