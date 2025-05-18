import pytest

# UI層のChatMessage型・初期化テスト
def test_ui_chatmessage():
    from ui.main import ChatMessage
    msg = ChatMessage("hello", is_user=True)
    assert msg.text == "hello"
    assert msg.is_user is True

# UI層の初期化・Myrdal連携テスト（最低限）
def test_ui_myrdal_integration():
    from ui.main import MyrdaIChatUI
    class DummyPage:
        def add(self, *args, **kwargs):
            pass
    ui = MyrdaIChatUI(page=DummyPage())
    assert hasattr(ui, "add_message") 