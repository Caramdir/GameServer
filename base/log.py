import logging
import logging.config

import config

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'file': {
            'formatter': 'standard',
            'level': 'DEBUG' if config.DEVTEST else "INFO",
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config.main_log_file,
            'maxBytes': 1024*1024,
            'backupCount': 5,
        },
        'console': {
            'formatter': 'standard',
            'level': 'DEBUG' if config.DEVTEST else "INFO",
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'DEBUG' if config.DEVTEST else "INFO",
            'propagate': False
        }
    }
}

if config.DEVTEST:
    log_config['loggers']['']['handlers'] = ["file", "console"]

logging.config.dictConfig(log_config)

# This is just for not breaking old code.
# New code should get a logger in the recommended way via logging.getLogger(__name__)
main_log = logging.getLogger("main_log")
