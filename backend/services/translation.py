from __future__ import annotations

from typing import List

from backend.core.logging import logger


class TranslationService:
    """Translation service supporting multiple backends."""

    @classmethod
    def translate(
        cls,
        texts: List[str],
        source_language: str,
        target_language: str,
    ) -> List[str]:
        """
        Translate texts from source to target language.
        
        Args:
            texts: List of text segments to translate
            source_language: Source language code (e.g., "zh", "en")
            target_language: Target language code (e.g., "en", "ja")
            
        Returns:
            List of translated text segments
        """
        if source_language == target_language:
            logger.info("Source and target language are the same, skipping translation")
            return texts

        logger.info(
            "Translating %d segments from %s to %s",
            len(texts),
            source_language,
            target_language,
        )

        # Try online translation services first
        try:
            return cls._translate_with_llm(texts, source_language, target_language)
        except Exception as e:
            logger.warning("LLM translation failed: %s, trying offline fallback", e)
            return cls._translate_offline(texts, source_language, target_language)

    @classmethod
    def _translate_with_llm(
        cls,
        texts: List[str],
        source_language: str,
        target_language: str,
    ) -> List[str]:
        """Translate using LLM API (OpenAI, Anthropic, etc.)."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package required for LLM translation")

        client = OpenAI()
        
        language_names = {
            "zh": "Chinese", "en": "English", "ja": "Japanese",
            "ko": "Korean", "es": "Spanish", "fr": "French",
            "de": "German", "ru": "Russian", "pt": "Portuguese",
            "it": "Italian", "ar": "Arabic", "hi": "Hindi",
        }
        
        source_name = language_names.get(source_language, source_language)
        target_name = language_names.get(target_language, target_language)
        
        prompt = f"""You are a professional translator. Translate the following {source_name} text to {target_name}.

Requirements:
- Maintain the original tone and style
- Keep the same length as much as possible
- Preserve any names, technical terms, or proper nouns
- Output ONLY the translated text, one line per segment

Segments to translate:
"""
        for i, text in enumerate(texts):
            prompt += f"{i+1}. {text}\n"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        translated = response.choices[0].message.content.strip().split("\n")
        # Clean up numbering
        result = []
        for line in translated:
            line = line.strip()
            # Remove leading numbers like "1. " or "1)"
            if line and line[0].isdigit():
                parts = line.split(".", 1)
                if len(parts) > 1:
                    line = parts[1].strip()
            result.append(line)

        # Ensure we have same count
        while len(result) < len(texts):
            result.append(texts[len(result)])

        logger.info("LLM translation completed")
        return result[:len(texts)]

    @classmethod
    def _translate_offline(
        cls,
        texts: List[str],
        source_language: str,
        target_language: str,
    ) -> List[str]:
        """Offline translation using local NMT models."""
        try:
            from transformers import MarianMTModel, MarianTokenizer
        except ImportError:
            logger.warning("transformers not installed, returning original texts")
            return texts

        model_name = f"Helsinki-NLP/opus-mt-{source_language}-{target_language}"
        
        try:
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
        except Exception as e:
            logger.warning(f"Could not load model {model_name}: {e}")
            # Try reverse direction
            model_name_rev = f"Helsinki-NLP/opus-mt-{target_language}-{source_language}"
            try:
                tokenizer = MarianTokenizer.from_pretrained(model_name_rev)
                model = MarianMTModel.from_pretrained(model_name_rev)
            except Exception:
                logger.warning("No suitable translation model found, returning originals")
                return texts

        results = []
        for text in texts:
            inputs = tokenizer(text, return_tensors="pt", padding=True)
            translated = model.generate(**inputs)
            decoded = tokenizer.decode(translated[0], skip_special_tokens=True)
            results.append(decoded)

        logger.info("Offline translation completed")
        return results


# Language code mapping for common languages
LANGUAGE_CODE_MAP = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese", 
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ru": "Russian",
    "pt": "Portuguese",
    "it": "Italian",
    "ar": "Arabic",
    "hi": "Hindi",
    "th": "Thai",
    "vi": "Vietnamese",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "cs": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "id": "Indonesian",
    "ms": "Malay",
    "ro": "Romanian",
    "uk": "Ukrainian",
}
