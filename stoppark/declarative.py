import sys

from PyQt4.QtCore import QUrl, QObject, pyqtProperty, pyqtSlot
from PyQt4.QtGui import QApplication, QColor
from PyQt4.QtDeclarative import QDeclarativeView
import random

def colorPairs(max):
    # capitalize the first letter
    colors = []
    for c in QColor.colorNames():
        colors.append(str(c[0]).upper() + str(c)[1:])

    # combine two colors, e.g. "lime skyblue"
    combinedColors = []
    num = len(colors)
    for i in range(num):
        for j in range(num):
            combinedColors.append("%s %s" % (colors[i], colors[j]))

    # randomize it
    colors = []
    while len(combinedColors):
        i = random.randint(0, len(combinedColors) - 1)
        colors.append(combinedColors[i])
        del(combinedColors[i])
        if len(colors) == max:
            break

    return colors


app = QApplication(sys.argv)

view = QDeclarativeView()
view.setSource(QUrl('view.qml'))
view.setResizeMode(QDeclarativeView.SizeViewToRootObject)

class Tariff(QObject):
    def __init__(self, title):
        QObject.__init__(self)
        self._title = title

    @pyqtProperty(str)
    def title(self):
        return self._title

    @pyqtProperty(str)
    def note(self):
        return 'Note'


root = view.rootObject()
tariffs = [Tariff(title) for title in colorPairs(10)]
root.set_tariffs(tariffs)


class Payment(QObject):
    def __init__(self, ticket, tariff):
        QObject.__init__(self, ticket)
        self.destroyed.connect(self.handleDestroyed)
        #self.ticket = ticket
        self.tariff = tariff

    def __del__(self):
        print 'Payment.__del__'

    def handleDestroyed(self, source):
        print '~Payment', source

    @pyqtProperty(str, constant=True)
    def explanation(self):
        return 'Explanation'


class Ticket(QObject):
    def __init__(self):
        QObject.__init__(self)
        #self.destroyed.connect(self.handleDestroyed)

    @pyqtSlot(str, result=QObject)
    def pay(self, tariff):
        #self.payment = Payment(self, tariff)
        #return self.payment
        return Payment(self, tariff)

    def __del__(self):
        print 'Ticket.__del__'

    def handleDestroyed(self, source):
        print '~Ticket', source


ticket = Ticket()

root.setProperty('ticket', ticket)



view.show()

app.exec_()