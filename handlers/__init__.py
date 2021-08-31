import os; import sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from logging import getLogger, basicConfig, INFO, WARNING, DEBUG, FileHandler, \
    StreamHandler, Formatter, handlers
from logging.config import dictConfig

if not os.path.exists('logs'):
    os.makedirs('logs')

dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(filename)-12.12s] [%(levelname)-5.5s]  %(message)s'
        }
    },
    'handlers': {
        'consoleHandler': {
            'level': 'WARNING',
            'formatter': 'default',
            'class': 'logging.StreamHandler'
        },
        'fileHandler': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/lorgnette.log',
            'maxBytes': 5242880,
            'backupCount': 20
        }        
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['consoleHandler', 'fileHandler']
    }
})
