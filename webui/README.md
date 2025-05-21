# Myrdal API サーバー

Myrdal AIシステムのためのFastAPIベースのRESTful APIおよびWebSocketサーバー実装です。

## 概要

このAPIサーバーは、Myrdal AIエージェントとのチャット機能をWebアプリケーションやその他のクライアントから利用できるようにします。RESTful APIエンドポイントとWebSocketインターフェースの両方を提供し、リアルタイムおよび非同期の通信をサポートします。

## 機能

- RESTful APIによるチャット機能
- WebSocketによるリアルタイムメッセージストリーミング
- シンプルなWebUIインターフェース
- 熟考過程（思考ステップ）の表示機能
- マークダウン形式のメッセージサポート

## 必要条件

- Python 3.12以上
- FastAPI
- Uvicorn
- その他の依存関係は`pyproject.toml`に記載

## インストールと実行

1. リポジトリをクローンまたはダウンロード:
```bash
git clone <リポジトリURL>
cd Myrdal4
```

2. 依存関係をインストール:
```bash
pip install -e .
```

3. APIサーバーを起動:
```bash
cd webui
python run.py
```

4. ブラウザで次のURLにアクセス:
   - WebUI: http://localhost:8000/
   - API ドキュメント: http://localhost:8000/api/docs

## APIエンドポイント

### RESTful API

- `POST /api/chat` - チャットメッセージを送信し、応答を取得
- `GET /api/health` - サーバーヘルスチェック

### WebSocket

- `/ws/chat` - リアルタイムチャット用WebSocketインターフェース

詳細なAPIドキュメントは、サーバー起動後に http://localhost:8000/api/docs でアクセスできます。

## 開発情報

- FastAPI 0.115.0以上
- フロントエンドはHTML/CSS/JavaScriptで実装
- WebSocketによるストリーミングはリアルタイムのAI応答を提供
- マークダウン（marked.js）を使用したリッチテキスト表示

## ライセンス

このプロジェクトのライセンス情報については、リポジトリのLICENSEファイルを参照してください。
