import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


def translate_to_fa(text: str) -> str:
    if not text or not text.strip():
        return ""
    try:
        chunk = text[:4999]
        return GoogleTranslator(source="auto", target="fa").translate(chunk)
    except Exception as e:
        logger.warning("Translation failed: %s", e)
        return text
