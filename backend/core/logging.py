import logging
import sys

from .config import settings


def setup_logging() -> logging.Logger:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"

    logging.basicConfig(level=level, format=fmt, handlers=[logging.StreamHandler(sys.stdout)])
    for noisy in ("httpx", "httpcore", "multipart", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("video_dubbing")


logger = setup_logging()
