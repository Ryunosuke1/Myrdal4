from langdetect import detect
from transformers import pipeline

class MultilingualUnderstanding:
    def __init__(self, translation_model="Helsinki-NLP/opus-mt-en-ROMANCE"):
        self.translator = pipeline("translation", model=translation_model)
    async def detect_language(self, text: str) -> str:
        return detect(text)
    async def translate(self, text: str, target_lang="en") -> str:
        # transformersのpipelineはtarget_langを自動判別しないため、モデル選択で対応
        result = self.translator(text)
        return result[0]["translation_text"] if result else text 