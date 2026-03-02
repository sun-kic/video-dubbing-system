import enum


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LanguageCode(str, enum.Enum):
    ZH = "zh"
    EN = "en"
    JA = "ja"
    KO = "ko"
    ES = "es"
    FR = "fr"
    DE = "de"
    RU = "ru"
    PT = "pt"
    AR = "ar"


class TtsEngine(str, enum.Enum):
    XTTS = "xtts"
    EDGE_TTS = "edge-tts"
    OPENAI = "openai"
