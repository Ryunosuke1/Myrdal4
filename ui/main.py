import flet as ft
import asyncio
import time
from typing import Optional, List, Dict, Any, cast
import random
import sys
import os
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    UserInputRequestedEvent,
    TextMessage
)

# パスを追加して myrdal モジュールを見つけられるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from myrdal.main import Myrdal

# Nordic color palette
class NordicColors:
    # Primary colors
    BLUE = "#5E81AC"  # Nordic blue
    RED = "#BF616A"   # Nordic red
    GREEN = "#A3BE8C" # Nordic green
    YELLOW = "#EBCB8B" # Nordic yellow
    
    # Neutrals
    WHITE = "#ECEFF4"  # Snow Storm 1
    LIGHT_GRAY = "#E5E9F0"  # Snow Storm 2
    GRAY = "#D8DEE9"  # Snow Storm 3
    DARK_GRAY = "#4C566A"  # Nord 3
    DARKER_GRAY = "#3B4252"  # Nord 1
    DARKEST_GRAY = "#2E3440"  # Nord 0
    
    # Accent colors
    TEAL = "#8FBCBB"  # Nord 7
    CYAN = "#88C0D0"  # Nord 8
    LIGHT_BLUE = "#81A1C1"  # Nord 9
    PURPLE = "#B48EAD"  # Nord 15

class ChatMessage:
    def __init__(self, text: str, is_user: bool, timestamp: float = None):
        self.text = text
        self.is_user = is_user
        self.timestamp = timestamp or time.time()
        self.id = f"{int(self.timestamp * 1000)}_{random.randint(1000, 9999)}"

class MyrdaIChatUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.myrdal = Myrdal()
        self.messages = []  # [(text, is_user, deliberation_id)]
        self.deliberations = {}  # {回答ID: [熟考過程リスト]}
        self.answer_count = 0
        self.initialized = False
        self.is_processing = False
        self.page.title = "Myrdal Chat"
        self.page.bgcolor = NordicColors.DARKEST_GRAY
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.on_resize = self.on_page_resize
        self.chat_column = ft.ListView(expand=True, spacing=8, auto_scroll=True, padding=16)
        self.input_field = ft.TextField(
            hint_text="メッセージを入力...",
            border_radius=30,
            filled=True,
            bgcolor=NordicColors.DARKER_GRAY,
            color=NordicColors.WHITE,
            border_color=NordicColors.DARK_GRAY,
            cursor_color=NordicColors.BLUE,
            text_size=16,
            content_padding=ft.padding.only(left=20, top=14, right=20, bottom=14),
            expand=True,
            on_submit=self.send_message,
        )
        self.send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=NordicColors.BLUE,
            icon_size=24,
            tooltip="送信",
            on_click=self.send_message,
        )
        self.input_row = ft.Row([
            self.input_field,
            self.send_button
        ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
        self.loading_indicator = ft.Row([
            ft.ProgressRing(width=18, height=18, stroke_width=2, color=NordicColors.BLUE),
            ft.Text("Myrdalが思考中...", color=NordicColors.LIGHT_GRAY, size=14)
        ], alignment=ft.MainAxisAlignment.START, visible=False)
        self.page.add(ft.SafeArea(
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Text("Myrdal AI チャット", size=22, weight=ft.FontWeight.BOLD, color=NordicColors.WHITE),
                        padding=ft.padding.symmetric(vertical=16),
                        alignment=ft.alignment.center,
                    ),
                    self.chat_column,
                    self.loading_indicator,
                    self.input_row
                ], expand=True, spacing=0),
                expand=True,
                bgcolor=NordicColors.DARKEST_GRAY,
                padding=ft.padding.all(0),
            ))
        )
        self.page.update()
        self.page.run_task(self.start)
        self.add_message("こんにちは！Myrdalです。何でも聞いてください。", is_user=False)

    async def start(self):
        if not self.initialized:
            await self.myrdal.ainit_team()
            self.initialized = True

    def send_message(self, e):
        message_text = self.input_field.value
        if not message_text or message_text.isspace() or self.is_processing:
            return
        self.add_message(message_text, is_user=True)
        self.input_field.value = ""
        self.page.update()
        self.page.run_task(self.on_user_message, message_text)

    async def on_user_message(self, message):
        await self.start()
        self.is_processing = True
        self.loading_indicator.visible = True
        self.page.update()
        current_deliberation = []
        resume_flag = True if self.messages else False
        answer_id = None
        # ストリーム用仮吹き出し
        ai_stream_text = ""
        ai_bubble = None
        ai_bubble_idx = None
        for idx, c in enumerate(self.chat_column.controls[::-1]):
            if hasattr(c, "is_streaming") and c.is_streaming:
                ai_bubble = c
                ai_bubble_idx = len(self.chat_column.controls) - 1 - idx
                break
        if ai_bubble is None:
            # 新規仮吹き出しを追加
            max_width = min(self.page.width * 0.75 - 100, 700)  # 画面幅の75%まで（ただし最大700px）
            ai_bubble = ft.Row([
                ft.CircleAvatar(bgcolor=NordicColors.BLUE, content=ft.Icon(ft.Icons.AUTO_AWESOME, color=NordicColors.WHITE, size=18), radius=18),
                ft.Container(
                    content=ft.Markdown(
                        value="", 
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        auto_follow_links=False
                    ),
                    bgcolor=NordicColors.BLUE,
                    padding=12,
                    border_radius=16,
                    margin=8,
                    alignment=ft.alignment.center_left,
                    width=max_width,
                    expand=True,
                ),
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            ai_bubble.is_streaming = True
            self.chat_column.controls.append(ai_bubble)
            ai_bubble_idx = len(self.chat_column.controls) - 1
            self.page.update()
        async for event in self.myrdal.interact_and_get_responses(message, resume=resume_flag):
            print("UI側message")
            print("---------------------")
            print(event)
            print("---------------------")
            # 直接TextMessageなどのメッセージオブジェクトの属性にアクセス
            if isinstance(event, TaskResult):
                msg_content = event.messages
                self.add_message(msg_content, False)
            elif isinstance(event, Response):
                if isinstance(event.chat_message, MultiModalMessage):
                    self.add_message(event.chat_message, False)
                else:
                    msg_content = event.chat_message.to_text()
                    self.add_message(msg_content, False)
            elif isinstance(event, UserInputRequestedEvent):
                pass
            elif isinstance(event, TextMessage):
                msg_content = event.chat_message.to_text()
                self.add_message(msg_content, False)
            else:
                if isinstance(event, ModelClientStreamingChunkEvent):
                    if event.source == "assistant" and isinstance(event.content, str) and "satisfied" in event.content:
                        answer_id = self.answer_count
                        self.answer_count += 1
                        self.messages.append(event.content)
                        self.deliberations[answer_id] = list(current_deliberation)
                        current_deliberation.clear()
                        self.chat_column.controls.pop(ai_bubble_idx)
                        self.add_message_with_deliberation(event.content, answer_id)
                        ai_bubble = None
                    elif isinstance(event.to_text(), str):
                        ai_stream_text += event.to_text()
        self.is_processing = False
        self.loading_indicator.visible = False
        self.page.update()

    def add_message_with_deliberation(self, content, answer_id):
        # AI吹き出し（左）
        max_width = min(self.page.width * 0.75 - 100, 700)  # 画面幅の75%まで（ただし最大700px）
        bubble = ft.Row([
            ft.CircleAvatar(bgcolor=NordicColors.BLUE, content=ft.Icon(ft.Icons.AUTO_AWESOME, color=NordicColors.WHITE, size=18), radius=18),
            ft.Container(
                content=ft.Markdown(
                    content, 
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    auto_follow_links=False
                ),
                bgcolor=NordicColors.BLUE,
                padding=12,
                border_radius=16,
                margin=8,
                alignment=ft.alignment.center_left,
                width=max_width,
                expand=True,
            ),
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        # 熟考過程パネル（サブ吹き出し/ポップオーバー）
        deliberation_panel = ft.Container(
            content=ft.Column([
                ft.Text(f"Step {i+1}: {d}", color=NordicColors.DARKER_GRAY, size=14) for i, d in enumerate(self.deliberations[answer_id])
            ]),
            bgcolor=NordicColors.LIGHT_GRAY,
            padding=10,
            border_radius=10,
            margin=8,
            visible=False,
            animate=ft.Animation(400, "easeInOut"),
            width=340,
            alignment=ft.alignment.center_left,
        )
        def toggle_deliberation(e):
            deliberation_panel.visible = not deliberation_panel.visible
            self.page.update()
        toggle_btn = ft.TextButton("🧠 熟考過程を見る", on_click=toggle_deliberation, bgcolor=NordicColors.TEAL, color=NordicColors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
        self.chat_column.controls.append(
            ft.Column([
                bubble,
                ft.Row([
                    toggle_btn,
                    deliberation_panel
                ], alignment=ft.MainAxisAlignment.START)
            ], alignment=ft.MainAxisAlignment.START)
        )
        self.page.update()

    def add_message(self, content, is_user):
        max_width = min(self.page.width * 0.75 - 100, 700)  # 画面幅の75%まで（ただし最大700px）
        # ユーザー吹き出し（右）
        if is_user:
            row = ft.Row([
                ft.Container(
                    content=ft.Markdown(
                        content,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        auto_follow_links=False
                    ),
                    bgcolor=NordicColors.GREEN,
                    padding=12,
                    border_radius=16,
                    margin=8,
                    alignment=ft.alignment.center_right,
                    width=max_width,
                    expand=True,
                ),
                ft.CircleAvatar(bgcolor=NordicColors.PURPLE, content=ft.Icon(ft.Icons.PERSON, color=NordicColors.WHITE, size=18), radius=18),
            ], alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.START)
        else:
            row = ft.Row([
                ft.CircleAvatar(bgcolor=NordicColors.BLUE, content=ft.Icon(ft.Icons.AUTO_AWESOME, color=NordicColors.WHITE, size=18), radius=18),
                ft.Container(
                    content=ft.Markdown(
                        value=content,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        auto_follow_links=False
                    ),
                    bgcolor=NordicColors.BLUE,
                    padding=12,
                    border_radius=16,
                    margin=8,
                    alignment=ft.alignment.center_left,
                    width=max_width,
                    expand=True,
                ),
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        self.chat_column.controls.append(row)
        self.page.update()

    def on_page_resize(self, e):
        # ウィンドウサイズが変更されたときに既存のメッセージバブルの幅を調整
        max_width = min(self.page.width * 0.75 - 100, 700)
        
        for message_row in self.chat_column.controls:
            if isinstance(message_row, ft.Row):
                for control in message_row.controls:
                    if isinstance(control, ft.Container) and hasattr(control, "content") and isinstance(control.content, ft.Markdown):
                        control.width = max_width
            elif isinstance(message_row, ft.Column):
                for inner_row in message_row.controls:
                    if isinstance(inner_row, ft.Row):
                        for control in inner_row.controls:
                            if isinstance(control, ft.Container) and hasattr(control, "content") and isinstance(control.content, ft.Markdown):
                                control.width = max_width
        
        self.page.update()

def main(page: ft.Page):
    chat_ui = MyrdaIChatUI(page)

if __name__ == "__main__":
    ft.app(target=main)
