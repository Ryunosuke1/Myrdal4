import flet as ft
import asyncio
import time
from typing import Optional, List, Dict, Any
import random
import sys
import os

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
        self.page.add(
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
            )
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
        await self.myrdal.interact_with_myrdal(message=message, resume=True if self.messages else False)
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
            ai_bubble = ft.Row([
                ft.CircleAvatar(bgcolor=NordicColors.BLUE, content=ft.Icon(ft.Icons.AUTO_AWESOME, color=NordicColors.WHITE, size=18), radius=18),
                ft.Container(
                    content=ft.Markdown(value="", selectable=True),
                    bgcolor=NordicColors.BLUE,
                    padding=12,
                    border_radius=16,
                    margin=8,
                    alignment=ft.alignment.center_left,
                ),
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            ai_bubble.is_streaming = True
            self.chat_column.controls.append(ai_bubble)
            ai_bubble_idx = len(self.chat_column.controls) - 1
            self.page.update()
        async for event in self.myrdal.get_responses_async():
            if hasattr(event, "message") and hasattr(event.message, "content"):
                msg = event.message
                if getattr(msg, "role", None) == "considering":
                    current_deliberation.append(msg.content)
                elif getattr(msg, "role", None) == "assistant" and "satisfied" in msg.content:
                    answer_id = self.answer_count
                    self.answer_count += 1
                    self.messages.append((msg.content, False, answer_id))
                    self.deliberations[answer_id] = list(current_deliberation)
                    current_deliberation.clear()
                    # 吹き出しを確定し熟考パネルを追加
                    self.chat_column.controls.pop(ai_bubble_idx)
                    self.add_message_with_deliberation(msg.content, answer_id)
                    ai_bubble = None
                else:
                    # ストリーム途中のAI出力を仮吹き出しに上書き
                    ai_stream_text += msg.content
                    if ai_bubble is not None:
                        ai_bubble.controls[1].content.value = ai_stream_text
                        self.page.update()
        self.is_processing = False
        self.loading_indicator.visible = False
        self.page.update()

    def add_message_with_deliberation(self, content, answer_id):
        # AI吹き出し（左）
        bubble = ft.Row([
            ft.CircleAvatar(bgcolor=NordicColors.BLUE, content=ft.Icon(ft.Icons.AUTO_AWESOME, color=NordicColors.WHITE, size=18), radius=18),
            ft.Container(
                content=ft.SelectableText(content, color=NordicColors.WHITE, size=16),
                bgcolor=NordicColors.BLUE,
                padding=12,
                border_radius=16,
                margin=8,
                alignment=ft.alignment.center_left,
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
        # ユーザー吹き出し（右）
        if is_user:
            row = ft.Row([
                ft.Container(
                    content=ft.Markdown(content),
                    bgcolor=NordicColors.GREEN,
                    padding=12,
                    border_radius=16,
                    margin=8,
                    alignment=ft.alignment.center_right,
                ),
                ft.CircleAvatar(bgcolor=NordicColors.PURPLE, content=ft.Icon(ft.Icons.PERSON, color=NordicColors.WHITE, size=18), radius=18),
            ], alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.START)
        else:
            row = ft.Row([
                ft.CircleAvatar(bgcolor=NordicColors.BLUE, content=ft.Icon(ft.Icons.AUTO_AWESOME, color=NordicColors.WHITE, size=18), radius=18),
                ft.Container(
                    content=ft.Markdown(value=content),
                    bgcolor=NordicColors.BLUE,
                    padding=12,
                    border_radius=16,
                    margin=8,
                    alignment=ft.alignment.center_left,
                ),
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        self.chat_column.controls.append(row)
        self.page.update()

def main(page: ft.Page):
    chat_ui = MyrdaIChatUI(page)

if __name__ == "__main__":
    ft.app(target=main)
