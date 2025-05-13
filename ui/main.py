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
        self.messages: List[ChatMessage] = []
        self.message_controls: Dict[str, ft.Control] = {}
        self.is_processing = False
        self.setup_page()
        self.create_ui()
        
    # 遅延アニメーション用のヘルパーメソッド
    async def _delayed_animation(self, delay: float, callback):
        await asyncio.sleep(delay)
        callback()
        
    def setup_page(self):
        self.page.title = "Myrdal Chat"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.bgcolor = NordicColors.DARKEST_GRAY
        self.page.fonts = {
            "SF Pro": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
        }
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=NordicColors.BLUE,
                primary_container=NordicColors.LIGHT_BLUE,
                secondary=NordicColors.TEAL,
                background=NordicColors.DARKEST_GRAY,
                surface=NordicColors.DARKER_GRAY,
                on_primary=NordicColors.WHITE,
                on_secondary=NordicColors.WHITE,
                on_background=NordicColors.WHITE,
                on_surface=NordicColors.WHITE,
            ),
            font_family="SF Pro",
        )
        
    def create_ui(self):
        # Header
        self.header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(name=ft.Icons.AUTO_AWESOME, color=NordicColors.TEAL, size=24),
                    ft.Text("Myrdal", size=20, weight=ft.FontWeight.BOLD, color=NordicColors.WHITE),
                    ft.Container(expand=True),  # Spacerの代わりにexpand=Trueのコンテナを使用
                    ft.IconButton(
                        icon=ft.Icons.DARK_MODE,
                        icon_color=NordicColors.LIGHT_GRAY,
                        tooltip="Toggle theme",
                        on_click=self.toggle_theme,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=NordicColors.DARKER_GRAY,
            border_radius=ft.border_radius.only(bottom_left=12, bottom_right=12),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color="0x33000000",  # 20% 透明度の黒
                offset=ft.Offset(0, 2),
            ),
        )

        # Chat messages container
        self.messages_container = ft.ListView(
            expand=True,
            spacing=16,
            padding=20,
            auto_scroll=True,
        )

        # Input field
        self.input_field = ft.TextField(
            hint_text="Message Myrdal...",
            border_radius=30,
            filled=True,
            bgcolor=NordicColors.DARKER_GRAY,
            color=NordicColors.WHITE,
            border_color=NordicColors.DARK_GRAY,
            cursor_color=NordicColors.BLUE,
            text_size=16,
            content_padding=ft.padding.only(left=20, top=14, right=20, bottom=14),
            on_submit=self.send_message,
            expand=True,
        )
        
        # Send button with animation
        self.send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=NordicColors.BLUE,
            icon_size=24,
            tooltip="Send message",
            on_click=self.send_message,
            animate_opacity=300,
        )
        
        # Input container
        self.input_container = ft.Container(
            content=ft.Row(
                [
                    self.input_field,
                    self.send_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.padding.only(left=16, right=16, top=12, bottom=24),
            bgcolor=NordicColors.DARKEST_GRAY,
        )
        
        # Thinking indicator
        self.thinking_indicator = ft.Row(
            [
                ft.Container(
                    content=ft.ProgressRing(
                        width=16, 
                        height=16, 
                        stroke_width=2,
                        color=NordicColors.BLUE
                    ),
                    margin=ft.margin.only(right=10)
                ),
                ft.Text("Myrdal is thinking...", color=NordicColors.LIGHT_GRAY),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            visible=False,
        )
        
        # Main layout
        self.page.add(
            self.header,
            ft.Container(
                content=ft.Column(
                    [
                        self.messages_container,
                        self.thinking_indicator,
                        self.input_container,
                    ],
                    spacing=0,
                ),
                expand=True,
            ),
        )
        
        # Add welcome message
        self.add_message(ChatMessage(
            "Hello! I'm Myrdal, your AI assistant. How can I help you today?",
            is_user=False
        ))
        
    def toggle_theme(self, e):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = NordicColors.WHITE
            self.header.bgcolor = NordicColors.GRAY
            self.input_field.bgcolor = NordicColors.LIGHT_GRAY
            self.input_container.bgcolor = NordicColors.WHITE
            e.control.icon = ft.Icons.LIGHT_MODE
            e.control.icon_color = NordicColors.DARK_GRAY
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = NordicColors.DARKEST_GRAY
            self.header.bgcolor = NordicColors.DARKER_GRAY
            self.input_field.bgcolor = NordicColors.DARKER_GRAY
            self.input_container.bgcolor = NordicColors.DARKEST_GRAY
            e.control.icon = ft.Icons.DARK_MODE
            e.control.icon_color = NordicColors.LIGHT_GRAY
        self.page.update()
        
    def create_message_bubble(self, message: ChatMessage) -> ft.Control:
        is_user = message.is_user
        
        # Message bubble styling
        bubble_color = NordicColors.BLUE if is_user else NordicColors.DARKER_GRAY
        text_color = NordicColors.WHITE
        alignment = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
        
        # Avatar
        avatar = ft.Container(
            content=ft.Icon(
                name=ft.Icons.PERSON if is_user else ft.Icons.AUTO_AWESOME,
                color=NordicColors.WHITE,
                size=16,
            ),
            width=32,
            height=32,
            border_radius=16,
            bgcolor=NordicColors.PURPLE if is_user else NordicColors.TEAL,
            alignment=ft.alignment.center,
        )
        
        # Message text with animation
        message_text = ft.Text(
            message.text,
            color=text_color,
            size=16,
            selectable=True,
            no_wrap=False,
        )
        
        # Message container with animation
        message_container = ft.Container(
            content=message_text,
            bgcolor=bubble_color,
            border_radius=16,
            padding=ft.padding.all(12),
            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            animate_opacity=300,
            animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            opacity=0,
            scale=0.9,
        )
        
        # Row for avatar and message
        row_content = [avatar, ft.Container(width=8), message_container]
        if is_user:
            row_content = [message_container, ft.Container(width=8), avatar]
            
        # Complete message row
        message_row = ft.Row(
            row_content,
            alignment=alignment,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        
        # Animate the message appearing
        # アニメーションはシンプルに実装 - 非同期処理なし
        message_container.opacity = 1
        message_container.scale = 1
        
        return message_row
        
    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        message_control = self.create_message_bubble(message)
        self.message_controls[message.id] = message_control
        self.messages_container.controls.append(message_control)
        self.page.update()
        
    async def process_message(self, user_message: str):
        self.is_processing = True
        self.thinking_indicator.visible = True
        self.page.update()
        
        try:
            # Send message to Myrdal
            await self.myrdal.inteact_with_myrdal(user_message)
            
            # Get responses asynchronously
            responses = []
            async for response in self.myrdal.get_responses_async():
                if hasattr(response, 'message') and hasattr(response.message, 'content'):
                    responses.append(response.message.content)
            
            # If no responses, provide a fallback
            if not responses:
                responses = ["I'm processing your request. Let me think about that..."]
                
                # Simulate thinking time for demo purposes
                await asyncio.sleep(1.5)
                
                # Add some sample responses for demonstration
                sample_responses = [
                    "I've analyzed your request and here's what I found...",
                    "Based on my understanding, I would recommend...",
                    "That's an interesting question! Here's my perspective...",
                ]
                responses.append(random.choice(sample_responses))
            
            # Add each response as a separate message
            for response_text in responses:
                self.add_message(ChatMessage(response_text, is_user=False))
                await asyncio.sleep(0.5)  # Slight delay between multiple responses
                
        except Exception as e:
            error_message = f"Sorry, I encountered an error: {str(e)}"
            self.add_message(ChatMessage(error_message, is_user=False))
        
        finally:
            self.is_processing = False
            self.thinking_indicator.visible = False
            self.page.update()
    
    def send_message(self, e):
        message_text = self.input_field.value
        if not message_text or message_text.isspace() or self.is_processing:
            return
            
        # Add user message
        self.add_message(ChatMessage(message_text, is_user=True))
        
        # Clear input field
        self.input_field.value = ""
        self.page.update()
        
        # Process message asynchronously
        asyncio.create_task(self.process_message(message_text))

def main(page: ft.Page):
    chat_ui = MyrdaIChatUI(page)

if __name__ == "__main__":
    ft.app(main)
