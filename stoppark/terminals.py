from PyQt4 import uic
from PyQt4.QtCore import Qt, QSize, pyqtSignal, QEvent, QBasicTimer
from PyQt4.QtGui import QWidget, QStyledItemDelegate, QStandardItemModel, QStandardItem
from PyQt4.QtGui import QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem
from PyQt4.QtGui import QSizePolicy, QFont, QIcon, QSystemTrayIcon, QGestureRecognizer
from mainloop import Mainloop


class MouseTapAndHoldGestureRecognizer(QGestureRecognizer):
    def __init__(self, gesture_button=Qt.LeftButton):
        QGestureRecognizer.__init__(self)
        self.gesture_button = gesture_button
        self.position = None
        self.timer = None

    def recognize(self, gesture, watched, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == self.gesture_button:
            self.position = event.pos()
            self.timer = QBasicTimer()
            self.timer.start(1000, watched)
            return QGestureRecognizer.MayBeGesture

        if event.type() == QEvent.MouseMove and self.position is not None:
            if self.exceeds(event.pos()):
                return QGestureRecognizer.CancelGesture

        if event.type() == QEvent.Timer and self.position is not None:
            if event.timerId() == self.timer.timerId():
                return QGestureRecognizer.FinishGesture
            else:
                return QGestureRecognizer.CancelGesture

        if event.type() == QEvent.MouseButtonRelease and event.button() == self.gesture_button:
            if self.position is not None:
                return QGestureRecognizer.CancelGesture

        return QGestureRecognizer.Ignore

    def exceeds(self, pos):
        return (pos - self.position).manhattanLength() > 3

    def reset(self, state):
        self.position = None
        self.timer.stop()
        self.timer = None
        QGestureRecognizer.reset(self, state)


class TerminalWidget(QWidget):
    def __init__(self, mainloop, addr, title, parent=None):
        QWidget.__init__(self, parent)
        self.mainloop = mainloop
        self.addr = addr
        self.title = QLabel(title)
        self.title.setFont(QFont('Monospace', 16))
        self.message = QLabel('')
        self.message.setFont(QFont('Monospace', 13))
        self.bt_open = self.init_button('arrow-up-icon.png', QSize(50, 50))
        self.bt_close = self.init_button('arrow-down-icon.png', QSize(50, 50))

        info_layout = QVBoxLayout()
        info_layout.addWidget(self.title)

        layout = QHBoxLayout()
        layout.addLayout(info_layout)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding))

        self.options_layout = QHBoxLayout()
        layout.addLayout(self.options_layout)

        layout.addWidget(self.bt_open)
        layout.addWidget(self.bt_close)

        self.setLayout(layout)

        self.bt_open.clicked.connect(self.open)
        self.bt_close.clicked.connect(self.close)

        #self.tap_and_hold = MouseTapAndHoldGestureRecognizer()
        #self.tap_and_hold_type = QGestureRecognizer.registerRecognizer(self.tap_and_hold)
        #self.grabGesture(self.tap_and_hold_type)
        self.grabGesture(Qt.TapAndHoldGesture)

    def update_config(self):
        self.mainloop.update_config(self.addr)
        self.clear_config_layout()

    def init_config_layout(self):
        if self.options_layout.isEmpty():
            config_bt = self.init_button('settings-icon.png', QSize(50, 50))
            config_bt.clicked.connect(self.update_config)
            self.options_layout.addWidget(config_bt)

    def clear_config_layout(self):
        for i in reversed(range(self.options_layout.count())):
            self.options_layout.itemAt(i).widget().setParent(None)

    def gesture_event(self, event):
        #if event.gestureType() == self.tap_and_hold_type:
        #    self.init_config_layout()
        #    return True
        if event.gestureType() == Qt.TapAndHoldGesture:
            self.init_config_layout()
            return True
        return False

    def event(self, event):
        if event.type() == QEvent.Gesture:
            print self.addr, event
            for g in event.gestures():
                if g.state() != Qt.GestureFinished:
                    continue
                if self.gesture_event(g):
                    return event.setAccepted(g, True)

        return QWidget.event(self, event)

    def init_button(self, icon_filename, size):
        button = QPushButton(self)
        button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        button.setAutoFillBackground(True)
        button.setMinimumSize(size)
        button.setIcon(QIcon(icon_filename))
        button.setIconSize(size)
        return button

    def show_message(self, msg):
        print unicode(msg).encode('utf8')
        self.message.setText(msg)

    def set_style_color(self, color):
        return self.setStyleSheet("""
        TerminalWidget {
            background-color: qradialgradient(cx:0.5, cy:0.5, radius: 0.5, fx:0.7, fy:0.7, stop:0 %s, stop:1 white);
        }""" % (color,))

    def set_state(self, state):
        if not self.isEnabled():
            return
        if state == 'active':
            self.set_style_color('green')
        elif state == 'inactive':
            self.set_style_color('red')
        elif state == 'disabled':
            self.set_style_color('gray')
        else:
            self.set_style_color('white')
        self.setAutoFillBackground(True)

    def open(self):
        self.mainloop.terminal_open(self.addr)

    def close(self):
        self.mainloop.terminal_close(self.addr)


class TerminalDelegate(QStyledItemDelegate):
    def __init__(self, mainloop, titles, parent=None):
        QStyledItemDelegate.__init__(self, parent)
        self.mainloop = mainloop
        self.titles = titles
        self.editors = {}

    def report(self, addr, message):
        self.editors[addr].show_message(message)

    def state(self, addr, state):
        self.editors[addr].set_state(state)

    def paint(self, painter, option, index):
        pass

    #noinspection PyPep8Naming
    def createEditor(self, parent, option, index):
        addr = index.model().data(index, Qt.EditRole).toInt()[0]
        editor = TerminalWidget(self.mainloop, addr, self.titles[addr], parent=parent)
        self.editors[addr] = editor
        return editor

    #noinspection PyPep8Naming
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    #noinspection PyPep8Naming
    def sizeHint(self, option, index):
        return QSize(315, 80)


class Terminals(QWidget):
    ready = pyqtSignal(bool)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.ui = uic.loadUiType('terminal.ui')[0]()
        self.ui.setupUi(self)

        self.notifier = QSystemTrayIcon(QIcon('arrow-up-icon.png'), self)
        self.notifier.show()

        self.model = None
        self.mainloop = None
        self.delegate = None

        self.update_model()

    def test_display(self):
        if self.mainloop:
            self.mainloop.test_display()

    def update_device_config(self):
        if self.mainloop:
            self.mainloop.update_config()

    def terminal_open(self, addr):
        if self.mainloop:
            self.mainloop.terminal_open(addr)

    def terminal_close(self, addr):
        if self.mainloop:
            self.mainloop.terminal_close(addr)

    def update_model(self):
        if self.mainloop:
            self.mainloop.state.disconnect()
            self.mainloop.ready.disconnect()
            self.mainloop.notify.disconnect()

            [self.ui.terminals.closePersistentEditor(self.model.index(row, 0))
             for row in xrange(self.model.rowCount())]
            self.mainloop.stop()

            self.mainloop = None

        self.mainloop = Mainloop(parent=self)
        self.mainloop.ready.connect(self.on_mainloop_ready)
        self.mainloop.notify.connect(lambda title, msg: self.notifier.showMessage(title, msg))
        self.mainloop.start()

    def on_mainloop_ready(self, ok, titles):
        if ok:
            self.model = QStandardItemModel(len(titles), 1)
            [self.model.setItem(i, QStandardItem(str(addr))) for i, addr in enumerate(titles.keys())]

            self.delegate = TerminalDelegate(self.mainloop, titles)
            self.mainloop.report.connect(self.delegate.report)
            self.mainloop.state.connect(self.delegate.state)

            self.ui.terminals.setModel(self.model)
            self.ui.terminals.setItemDelegateForColumn(0, self.delegate)
            [self.ui.terminals.openPersistentEditor(self.model.index(row, 0))
             for row in xrange(self.model.rowCount())]

            self.mainloop.db.free_places_update.connect(self.ui.free_places.setValue)
            self.mainloop.update_config()
        else:
            self.model = None
            self.mainloop = None

        self.ready.emit(ok)

    def stop_mainloop(self):
        if self.mainloop:
            self.mainloop.stop()
