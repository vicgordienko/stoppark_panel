import u2py.config
import sys
import os
from PyQt4.QtSql import QSqlDatabase

u2py.config.raise_on_io_error = False

win32 = sys.platform == 'win32'

stoppark_dir = os.path.join('.' if win32 else os.environ['HOME'], '.stoppark')
if not os.path.exists(stoppark_dir):
    os.makedirs(stoppark_dir)

u2py.config.db_filename = os.path.join(stoppark_dir, 'db')

#noinspection PyCallByClass,PyTypeChecker
QDB = QSqlDatabase.addDatabase("QSQLITE")
QDB.setDatabaseName(u2py.config.db_filename)
QDB.open()

if sys.platform == 'linux2':
    u2py.config.reader_path = [
        #{'path': '/dev/ttyUSB0', 'baud': 38400, 'parity': 2, 'impl': 'asio-mt' }
        #{'path': '127.0.0.1:1200', 'impl': 'tcp' },
        {'path': '/tmp/stream', 'impl': 'unix'},
    ]
else:
    u2py.config.reader_path = [
        {'path': '\\\\.\\COM4', 'baud': 38400, 'parity': 2, 'impl': 'asio-mt'}
    ]

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
