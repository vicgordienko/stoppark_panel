import u2py.config
import sys
import os


u2py.config.raise_on_io_error = False

win32 = sys.platform == 'win32'

stoppark_dir = os.path.join('.' if win32 else os.environ['HOME'], '.stoppark')
if not os.path.exists(stoppark_dir):
    os.makedirs(stoppark_dir)

u2py.config.db_filename = os.path.join(stoppark_dir, 'db')
db_filename = u2py.config.db_filename

if sys.platform == 'linux2':
    u2py.config.reader_path = [
        {'path': '/dev/ttyUSB0', 'baud': 38400, 'parity': 2, 'impl': 'asio-mt'}
        #{'path': '127.0.0.1:1200', 'impl': 'tcp' },
        #{'path': '/tmp/stream', 'impl': 'unix'},
    ]
    DISPLAY_PEER = '/tmp/screen'
    TICKET_PEER = '/tmp/bar'
    CARD_PEER = '/tmp/card'
    PRINTER_PEER = '/tmp/printer'
else:
    u2py.config.reader_path = [
        {'path': '\\\\.\\COM3', 'baud': 38400, 'parity': 2, 'impl': 'asio-mt'}
    ]
    DISPLAY_PEER = ('127.0.0.1', 1000)
    TICKET_PEER = ('127.0.0.1', 1001)
    CARD_PEER = ('127.0.0.1', 1002)
    PRINTER_PEER = ('127.0.0.1', 1003)

LOCAL_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT = '%y-%m-%d'
DATE_USER_FORMAT = '%d/%m/%y'
DATETIME_FORMAT = '%y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FULL = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_USER = '%d/%m/%y %H:%M:%S'


def setup_logging(handler=None):
    if handler is None:
        handler = 'console'

    import logging.config

    logging.config.dictConfig({
        'version': 1,  # Configuration schema in use; must be 1 for now
        'formatters': {
            'standard': {
                'format': ('%(asctime)s '
                           '%(levelname)-8s %(message)s')}},
        'handlers': {'u2': {'backupCount': 10,
                            'class': 'logging.handlers.RotatingFileHandler',
                            'filename': os.path.join(stoppark_dir, 'log'),
                            'formatter': 'standard',
                            'level': 'DEBUG',
                            'maxBytes': 10000000},
                     'console': {
                     'class': 'logging.StreamHandler',
                     'formatter': 'standard'
                     }},
        'root': { 'level': 'ERROR', 'handlers': [handler]},
    })
