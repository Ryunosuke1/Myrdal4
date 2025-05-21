import asyncio
import sys
import os
import time
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    UserInputRequestedEvent,
    TextMessage,
    ThoughtEvent
)

# パスを追加して myrdal モジュールを見つけられるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from myrdal.main import Myrdal

# モデルの定義
class ChatMessage(BaseModel):
    text: str
    is_user: bool
    timestamp: Optional[float] = None
    id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    resume: bool = False

class ChatResponse(BaseModel):
    message: str
    is_user: bool = False
    deliberations: List[str] = []
    timestamp: float = None
    id: Optional[str] = None

# FastAPIアプリケーションの作成
app = FastAPI(title="Myrdal AI API", 
              description="FastAPI based REST API for Myrdal AI",
              version="0.1.0")

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="webui/static"), name="static")
templates = Jinja2Templates(directory="webui/templates")

# Myrdalインスタンスを保持する
myrdal_instance = Myrdal()
initialized = False

# WebSocketコネクションのリスト
active_connections: List[WebSocket] = []

async def initialize_myrdal():
    global initialized
    if not initialized:
        await myrdal_instance.ainit_team()
        initialized = True

@app.on_event("startup")
async def startup_event():
    # アプリ起動時にMyrdal初期化を開始
    background_tasks = BackgroundTasks()
    background_tasks.add_task(initialize_myrdal)

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/docs", response_class=HTMLResponse)
async def get_api_docs(request: Request):
    return templates.TemplateResponse("api_docs.html", {"request": request})

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    """
    RESTful APIエンドポイントでメッセージを送信し、応答を取得する
    """
    global initialized
    if not initialized:
        # 初期化が完了していない場合は初期化する
        await initialize_myrdal()
    
    message = chat_request.message
    resume = chat_request.resume
    
    # 応答を取得するためのリスト
    response_text = ""
    deliberations = []
    
    try:
        # interact_and_get_responsesでレスポンスを取得
        async for event in myrdal_instance.interact_and_get_responses(message, resume=resume):
            # タイプに基づいて応答を処理（isinstanceを使用）
            if isinstance(event, TaskResult):
                msg_content = event.messages
                response_text = msg_content
            elif isinstance(event, Response):
                if hasattr(event, "chat_message"):
                    if isinstance(event.chat_message, MultiModalMessage):
                        response_text = str(event.chat_message)
                    else:
                        response_text = event.chat_message.to_text()
            elif isinstance(event, UserInputRequestedEvent):
                # UserInputRequestedEventは無視
                pass
            elif isinstance(event, TextMessage):
                if hasattr(event, "chat_message"):
                    response_text = event.chat_message.to_text()
            elif isinstance(event, ModelClientStreamingChunkEvent):
                if event.source == "assistant" and isinstance(event.content, str):
                    if "satisfied" in event.content:
                        # 回答が確定した場合
                        response_text = event.content
                        # 熟考過程があれば保存
                        if hasattr(event, "thoughts") and event.thoughts:
                            deliberations.extend(event.thoughts)
                    elif isinstance(event.to_text(), str):
                        # ストリーミングテキストを追加
                        response_text += event.to_text()
            # その他のイベントタイプ（フォールバック）
            elif hasattr(event, "to_text") and callable(event.to_text):
                response_text += event.to_text()
            elif hasattr(event, "content") and event.content:
                response_text = event.content
                if hasattr(event, "thoughts") and event.thoughts:
                    deliberations.extend(event.thoughts)
            elif hasattr(event, "chat_message"):
                if hasattr(event.chat_message, "to_text") and callable(event.chat_message.to_text):
                    response_text = event.chat_message.to_text()
                elif hasattr(event.chat_message, "content"):
                    response_text = event.chat_message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    
    # タイムスタンプとIDを生成
    timestamp = time.time()
    message_id = f"{int(timestamp * 1000)}_{int(timestamp % 1) * 1000}"
    
    return ChatResponse(
        message=response_text,
        deliberations=deliberations,
        timestamp=timestamp,
        id=message_id
    )

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocketエンドポイントで双方向通信を行う
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # 初期化が完了していない場合は初期化する
        global initialized
        if not initialized:
            await initialize_myrdal()
            initialized = True
            
        # 初期メッセージを送信
        welcome_message = {
            "message": "こんにちは！Myrdalです。何でも聞いてください。", 
            "is_user": False, 
            "timestamp": time.time(),
            "id": f"{int(time.time() * 1000)}_0000"
        }
        await websocket.send_json(welcome_message)
        
        # クライアントからのメッセージを処理するループ
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            resume = data.get("resume", False)
            
            # ユーザーメッセージの処理
            if user_message:
                # 応答を取得してストリーミング
                response_text = ""
                deliberations = []
                
                # 実行中のストリーミング更新
                is_streaming = True
                timestamp = time.time()
                message_id = f"{int(timestamp * 1000)}_{int(timestamp % 1) * 1000}"
                
                async for event in myrdal_instance.interact_and_get_responses(user_message, resume=resume):
                    # isinstanceを使用したイベントタイプ判定
                    if isinstance(event, TaskResult):
                        msg_content = event.messages
                        response_text = msg_content
                        await websocket.send_json({
                            "message": response_text,
                            "is_user": False,
                            "is_streaming": True,
                            "timestamp": timestamp,
                            "id": message_id
                        })
                    elif isinstance(event, Response):
                        if hasattr(event, "chat_message"):
                            if isinstance(event.chat_message, MultiModalMessage):
                                response_text = str(event.chat_message)
                            else:
                                response_text = event.chat_message.to_text()
                            await websocket.send_json({
                                "message": response_text,
                                "is_user": False,
                                "is_streaming": True,
                                "timestamp": timestamp,
                                "id": message_id
                            })
                    elif isinstance(event, UserInputRequestedEvent):
                        # UserInputRequestedEventは無視
                        pass
                    elif isinstance(event, TextMessage):
                        if hasattr(event, "chat_message"):
                            response_text = event.chat_message.to_text()
                            await websocket.send_json({
                                "message": response_text,
                                "is_user": False,
                                "is_streaming": True,
                                "timestamp": timestamp,
                                "id": message_id
                            })
                    elif isinstance(event, ModelClientStreamingChunkEvent):
                        if event.source == "assistant" and isinstance(event.content, str):
                            if "satisfied" in event.content:
                                # 回答が確定した場合
                                response_text = event.content
                                # 熟考過程があれば保存
                                if hasattr(event, "thoughts") and event.thoughts:
                                    deliberations.extend(event.thoughts)
                                await websocket.send_json({
                                    "message": response_text,
                                    "is_user": False,
                                    "is_streaming": True,
                                    "deliberations": deliberations,
                                    "timestamp": timestamp,
                                    "id": message_id
                                })
                            elif isinstance(event.to_text(), str):
                                # ストリーミングテキスト更新
                                new_text = event.to_text()
                                if new_text:
                                    response_text += new_text
                                    await websocket.send_json({
                                        "message": response_text,
                                        "is_user": False,
                                        "is_streaming": True,
                                        "timestamp": timestamp,
                                        "id": message_id
                                    })
                    # フォールバック処理
                    elif hasattr(event, "to_text") and callable(event.to_text):
                        new_text = event.to_text()
                        if new_text:
                            response_text += new_text
                            await websocket.send_json({
                                "message": response_text,
                                "is_user": False,
                                "is_streaming": True,
                                "timestamp": timestamp,
                                "id": message_id
                            })
                    elif hasattr(event, "content") and event.content:
                        response_text = event.content
                        # 熟考過程があれば保存
                        if hasattr(event, "thoughts") and event.thoughts:
                            deliberations.extend(event.thoughts)
                        await websocket.send_json({
                            "message": response_text,
                            "is_user": False,
                            "is_streaming": True,
                            "deliberations": deliberations,
                            "timestamp": timestamp,
                            "id": message_id
                        })
                    elif hasattr(event, "chat_message"):
                        if hasattr(event.chat_message, "to_text") and callable(event.chat_message.to_text):
                            response_text = event.chat_message.to_text()
                        elif hasattr(event.chat_message, "content"):
                            response_text = event.chat_message.content
                        await websocket.send_json({
                            "message": response_text,
                            "is_user": False,
                            "is_streaming": True,
                            "timestamp": timestamp,
                            "id": message_id
                        })
                
                # ストリーミング完了後の最終応答
                await websocket.send_json({
                    "message": response_text,
                    "is_user": False,
                    "is_streaming": False,
                    "deliberations": deliberations,
                    "timestamp": timestamp,
                    "id": message_id
                })
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        await websocket.close()

@app.get("/api/health")
async def health_check():
    """
    ヘルスチェックエンドポイント
    """
    return {"status": "ok", "initialized": initialized}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
