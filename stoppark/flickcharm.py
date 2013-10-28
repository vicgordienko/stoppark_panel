import copy
from PyQt4.QtCore import QObject, QEvent, Qt, QBasicTimer, QPoint
from PyQt4.QtGui import QMouseEvent, QCursor, QApplication


class FlickData(object):
    Steady = 0
    Pressed = 1
    ManualScroll = 2
    AutoScroll = 3
    Stop = 4

    def __init__(self):
        self.state = FlickData.Steady
        self.widget = None
        self.press_pos = QPoint(0, 0)
        self.offset = QPoint(0, 0)
        self.drag_pos = QPoint(0, 0)
        self.speed = QPoint(0, 0)
        self.q = 0
        self.ignored = []


class FlickCharmPrivate:
    def __init__(self):
        self.flick_data = {}
        self.ticker = QBasicTimer()


class FlickCharm(QObject):
    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.d = FlickCharmPrivate()

    def activate_on(self, widget):
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        viewport = widget.viewport()
        viewport.installEventFilter(self)
        widget.installEventFilter(self)
        self.d.flick_data[viewport] = FlickData()
        self.d.flick_data[viewport].widget = widget
        self.d.flick_data[viewport].state = FlickData.Steady

    def deactivate_on(self, widget):
        viewport = widget.viewport()
        viewport.removeEventFilter(self)
        widget.removeEventFilter(self)
        del (self.d.flick_data[viewport])

    #noinspection PyPep8Naming
    def eventFilter(self, obj, event):

        if not obj.isWidgetType():
            return False

        event_type = event.type()
        if event_type != QEvent.MouseButtonPress and \
            event_type != QEvent.MouseButtonRelease and \
                event_type != QEvent.MouseMove:
            return False

        if event.modifiers() != Qt.NoModifier:
            return False

        #if not self.d.flick_data.has_key(obj):
        if obj not in self.d.flick_data:
            return False

        data = self.d.flick_data[obj]
        found, new_ignored = remove_all(data.ignored, event)
        if found:
            data.ignored = new_ignored
            return False

        consumed = False

        if data.state == FlickData.Steady:
            if event_type == QEvent.MouseButtonPress:
                if event.buttons() == Qt.LeftButton:
                    consumed = True
                    data.state = FlickData.Pressed
                    data.press_pos = copy.copy(event.pos())
                    data.offset = scroll_offset(data.widget)

        elif data.state == FlickData.Pressed:
            if event_type == QEvent.MouseButtonRelease:
                consumed = True
                data.state = FlickData.Steady
                event1 = QMouseEvent(QEvent.MouseButtonPress,
                                     data.press_pos, Qt.LeftButton,
                                     Qt.LeftButton, Qt.NoModifier)
                event2 = QMouseEvent(event)
                data.ignored.append(event1)
                data.ignored.append(event2)
                QApplication.postEvent(obj, event1)
                QApplication.postEvent(obj, event2)
            elif event_type == QEvent.MouseMove:
                diff = data.press_pos - event.pos()
                if diff.x()**2 + diff.y()**2 > 25:
                    consumed = True
                    data.state = FlickData.ManualScroll
                    data.dragPos = QCursor.pos()
                    if not self.d.ticker.isActive():
                        self.d.ticker.start(20, self)

        elif data.state == FlickData.ManualScroll:
            if event_type == QEvent.MouseMove:
                consumed = True
                pos = event.pos()
                delta = pos - data.press_pos
                set_scroll_offset(data.widget, data.offset - delta)
            elif event_type == QEvent.MouseButtonRelease:
                consumed = True
                data.state = FlickData.AutoScroll

        elif data.state == FlickData.AutoScroll:
            if event_type == QEvent.MouseButtonPress:
                consumed = True
                data.state = FlickData.Stop
                data.speed = QPoint(0, 0)
            elif event_type == QEvent.MouseButtonRelease:
                consumed = True
                data.state = FlickData.Steady
                data.speed = QPoint(0, 0)

        elif data.state == FlickData.Stop:
            if event_type == QEvent.MouseButtonRelease:
                consumed = True
                data.state = FlickData.Steady
            elif event_type == QEvent.MouseMove:
                consumed = True
                data.state = FlickData.ManualScroll
                data.drag_pos = QCursor.pos()
                data.press_pos = copy.copy(event.pos())
                data.offset = scroll_offset(data.widget)
                if not self.d.ticker.isActive():
                    self.d.ticker.start(20, self)

        return consumed

    #noinspection PyPep8Naming
    def timerEvent(self, event):
        count = 0
        for data in self.d.flick_data.values():
            if data.state == FlickData.ManualScroll:
                count += 1
                data.q = (data.q + 1) % 4
                if data.q == 0:
                    cursorPos = QCursor.pos()
                    data.speed = (cursorPos - data.dragPos) * 8
                    data.dragPos = cursorPos
            elif data.state == FlickData.AutoScroll:
                count += 1
                data.speed = decelerate(data.speed)
                p = scroll_offset(data.widget)
                set_scroll_offset(data.widget, p - data.speed)
                if data.speed == QPoint(0, 0):
                    data.state = FlickData.Steady

        if count == 0:
            self.d.ticker.stop()

        QObject.timerEvent(self, event)


def scroll_offset(widget):
    x = widget.horizontalScrollBar().value()
    y = widget.verticalScrollBar().value()
    return QPoint(x, y)


def set_scroll_offset(widget, p):
    widget.horizontalScrollBar().setValue(p.x())
    widget.verticalScrollBar().setValue(p.y())


def decelerate(speed, a=1, max_val=64):
    x = bound(-max_val, speed.x(), max_val)
    y = bound(-max_val, speed.y(), max_val)
    if x > 0:
        x = max(0, x - a)
    elif x < 0:
        x = min(0, x + a)
    if y > 0:
        y = max(0, y - a)
    elif y < 0:
        y = min(0, y + a)
    return QPoint(x, y)


def bound(min_val, current, max_val):
    return max(min(current, max_val), min_val)


def remove_all(lst, val):
    found = False
    ret = []
    for element in lst:
        if element == val:
            found = True
        else:
            ret.append(element)
    return found, ret