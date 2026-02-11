import logging
import logging.config


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "level": "DEBUG",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "botocore": {"level": "ERROR"},
        "python-multipart": {"level": "ERROR"},
        "urllib3": {"level": "ERROR"},
        "multipart": {"level": "ERROR"},
        "multipart.multipart": {"level": "ERROR"},
        "httpx": {"level": "ERROR"},
    },
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
