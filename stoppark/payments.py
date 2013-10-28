from PyQt4 import uic
from PyQt4.QtCore import QObject, pyqtSignal, Qt, QRect, QRectF
from PyQt4.QtGui import QWidget, QGraphicsScene, QGraphicsItem, QFont, QStyle, QColor, QPainter, QFrame, QFontMetrics
from gevent import socket, spawn, sleep
from gevent.queue import Queue
from threading import Thread
from db import DB, Ticket
from flickcharm import FlickCharm
import time


class Reader(QObject):
    new_ticket = pyqtSignal(Ticket)
    payment_processed = pyqtSignal()
    tariffs_updated = pyqtSignal(list)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.thread = Thread(target=self._loop)
        self.db = None
        self.sock = None
        self.queue = None

    def _reader(self):
        try:
            while True:
                bar = self.sock.recv(128).strip(';?\n\r')
                print 'bar_read', time.time()

                ticket = self.db.get_ticket(bar)
                if not ticket:
                    Ticket.register(self.db, str(bar))
                    ticket = self.db.get_ticket(bar)

                print ticket

                print 'bar_processed', time.time()

                self.new_ticket.emit(ticket)

        except socket.error:
            print 'reader completed'

    def _process_payment(self, payment):
        payment.execute(self.db)
        self.payment_processed.emit()

    @staticmethod
    def _job():
        while True:
            sleep(2)

    def _tariff_updater(self):
        while True:
            self.tariffs_updated.emit(self.db.get_tariffs())
            sleep(60)

    def _loop(self):
        self.queue = Queue()
        self.db = DB()

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect('/tmp/bar')

        spawn(self._job)
        spawn(self._reader)
        spawn(self._tariff_updater)

        while True:
            payment = self.queue.get()

            if payment is not None:
                self._process_payment(payment)
            else:
                print 'got None'
                #[greenlet.kill() for greenlet in greenlets]
                break

        print 'reader loop completed'

    def start(self):
        self.thread.start()

    def pay(self, payment):
        if self.queue:
            self.queue.put(payment)
        else:
            print 'There is not queue to put payments.'

    def stop(self):
        if self.queue is not None:
            self.queue.put(None)
        else:
            print 'Already stopped'


ITEM_WIDTH = 500
ITEM_HEIGHT = 70


class TariffItem(QGraphicsItem):
    def __init__(self, tariff):
        QGraphicsItem.__init__(self)
        self.tariff = tariff
        self.str1 = tariff.name
        self.str2 = '(%i)' % (tariff.interval,)
        self.font1 = QFont("Lucida Grande")
        self.font2 = QFont("Lucida Grande")
        self.font1.setBold(True)
        self.font1.setPixelSize(ITEM_HEIGHT / 2)
        self.font2.setPixelSize(ITEM_HEIGHT / 2)
        self.offset = QFontMetrics(self.font1).width(self.str1) + 15

    def boundingRect(self):
        return QRectF(0, 0, ITEM_WIDTH, ITEM_HEIGHT)

    def paint(self, painter, option, widget):
        if option.state & QStyle.State_Selected:
            painter.fillRect(self.boundingRect(), QColor(0, 128, 240))
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.lightGray)
            painter.drawRect(self.boundingRect())
            painter.setPen(Qt.black)
        painter.setFont(self.font1)
        painter.drawText(QRect(10, 0, self.offset, ITEM_HEIGHT),
                         Qt.AlignVCenter, self.str1)
        painter.setFont(self.font2)
        painter.drawText(QRect(self.offset, 0, ITEM_WIDTH, ITEM_HEIGHT),
                         Qt.AlignVCenter, self.str2)


class Payments(QWidget):
    new_payment = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.tariffs = None
        self.payment = None
        self.scene = None

        self.ui = uic.loadUiType('payments.ui')[0]()
        self.ui.setupUi(self)

        self.ui.progress.setVisible(False)

        self.reader = Reader(self)
        self.reader.tariffs_updated.connect(self.update_tariffs)
        self.reader.start()

        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.pay.clicked.connect(self.pay)

        self.ui.tariffs.setRenderHints(QPainter.TextAntialiasing)
        self.ui.tariffs.setFrameShape(QFrame.NoFrame)

        self.flick = FlickCharm()
        self.flick.activate_on(self.ui.tariffs)

    def update_tariffs(self, tariffs):
        if self.tariffs is None:
            print 'update_tariffs A', tariffs
            self.ready_to_handle()
        else:
            print 'update_tariffs B'
        self.tariffs = tariffs

    def ready_to_handle(self):
        self.reader.new_ticket.connect(self.handle_ticket)
        self.ui.cancel.setEnabled(False)
        self.ui.pay.setEnabled(False)

    def ready_to_pay(self):
        self.reader.new_ticket.disconnect(self.handle_ticket)
        self.ui.cancel.setEnabled(True)
        self.ui.pay.setEnabled(True)

    def handle_ticket(self, ticket):
        self.ui.bar.setText(ticket.bar)
        self.new_payment.emit()

        self.scene = QGraphicsScene()
        self.scene.setItemIndexMethod(QGraphicsScene.NoIndex)

        for i, tariff in enumerate(self.tariffs):
            item = TariffItem(tariff)
            self.scene.addItem(item)
            item.setPos(i * ITEM_WIDTH, 0)
            item.setFlag(QGraphicsItem.ItemIsSelectable, True)

        self.scene.setItemIndexMethod(QGraphicsScene.BspTreeIndex)

        self.ui.tariffs.setScene(self.scene)

        self.scene.setItemIndexMethod(QGraphicsScene.BspTreeIndex)

        self.scene.selectionChanged.connect(lambda: self.handle_ticket_with_current_tariff(ticket))

    def handle_ticket_with_current_tariff(self, ticket):
        selected = self.scene.selectedItems()
        if not len(selected):
            print 'No selection'
            return
        tariff = selected[0].tariff
        if not hasattr(tariff, 'calc'):
            self.ui.explanation.setText('Unsupported tariff.')
            return

        self.payment = ticket.pay(tariff)
        if self.payment:
            self.ui.explanation.setText(self.payment.explanation())
            self.ready_to_pay()
        else:
            self.ui.explanation.setText('Already paid.')

    def pay(self):
        self.reader.payment_processed.connect(self.payment_completed)
        self.reader.pay(self.payment)
        self.ui.pay.setEnabled(False)
        self.ui.cancel.setEnabled(False)
        self.ui.progress.setVisible(True)

    def cancel(self):
        self.ui.explanation.setText('')
        self.ui.bar.setText('-')
        self.ready_to_handle()

    def payment_completed(self):
        self.ui.progress.setVisible(False)
        self.reader.payment_processed.disconnect(self.payment_completed)

        self.ui.explanation.setText(self.ui.explanation.text() + 'Paid.')
        self.ready_to_handle()

    def stop_reader(self):
        self.reader.stop()
