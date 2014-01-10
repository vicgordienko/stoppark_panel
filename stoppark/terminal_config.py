# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import Qt, QVariant, QSize, QEvent
from PyQt4.QtGui import QDialog, QFont, QHeaderView, QStyledItemDelegate
from PyQt4.QtGui import QApplication, QStyle, QStyleOptionViewItem, QColor
from PyQt4.QtSql import QSqlTableModel, QSqlDatabase
from config import db_filename
from i18n import language
_ = language.ugettext


#noinspection PyCallByClass,PyTypeChecker
QDB = QSqlDatabase.addDatabase("QSQLITE")
QDB.setDatabaseName(db_filename)
QDB.open()


class CenteredCheckBoxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        QStyledItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        value = index.data().toBool()

        style = QApplication.style()

        rect = style.subElementRect(QStyle.SE_CheckBoxIndicator, option)

        cx = option.rect.left() + max(option.rect.width()/2 - rect.width()/2, 0)
        cy = option.rect.top() + max(option.rect.height()/2 - rect.height()/2, 0)

        mod_option = QStyleOptionViewItem(option)
        mod_option.rect.moveTo(cx, cy)
        mod_option.rect.setSize(QSize(rect.width(), rect.height()))
        if value:
            mod_option.state |= QStyle.State_On

        style.drawPrimitive(QStyle.PE_IndicatorItemViewItemCheck, mod_option, painter)

    #noinspection PyPep8Naming
    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            value = model.data(index, Qt.CheckStateRole)
            model.setData(index, value ^ Qt.Checked, Qt.CheckStateRole)
            return True
        return QStyledItemDelegate.editorEvent(self, event, model, option, index)


class TerminalSqlTableModel(QSqlTableModel):
    def __init__(self, parent=None, db=None):
        QSqlTableModel.__init__(self, parent, db)
        self.headers = [_('Addr'), _('Title'), u'', u'']
        self.font = QFont("Monospace", 18)

    #noinspection PyPep8Naming,PyMethodOverriding
    def headerData(self, col, orientation, role):
        if role == Qt.FontRole:
            return self.font

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headers[col])
        return QVariant()

    def flags(self, index):
        flags = QSqlTableModel.flags(self, index)
        flags &= ~Qt.ItemIsEditable
        if index.column() == 2:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def set_option(self, row, value):
        print 'set_option', row, value
        for i in range(self.rowCount()):
            index = self.index(i, 3)
            if self.data(index, Qt.EditRole).toString() == value:
                self.dataChanged.emit(self.index(i, 0), index)
                self.setData(index, '', Qt.EditRole)

        self.dataChanged.emit(self.index(row, 0), self.index(row, 3))
        return self.setData(self.index(row, 3), value, Qt.EditRole)

    def get_color_by_option(self, index):
        option = QSqlTableModel.data(self, self.index(index.row(), 3)).toString()
        if option == 'left':
            return QColor(Qt.darkGreen)
        if option == 'right':
            return QColor(Qt.darkCyan)
        return QVariant()

    #noinspection PyMethodOverriding
    def data(self, index, role):
        if role == Qt.FontRole:
            return self.font

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        if role == Qt.BackgroundColorRole:
            return self.get_color_by_option(index)

        if index.column() == 2:
            value = QSqlTableModel.data(self, index, Qt.EditRole).toInt()[0] == 1
            if role == Qt.CheckStateRole:
                return Qt.Checked if value else Qt.Unchecked
            if role == Qt.EditRole or role == Qt.DisplayRole:
                return QVariant(value)
            return QVariant()
        return QSqlTableModel.data(self, index, role)

    #noinspection PyPep8Naming,PyMethodOverriding
    def setData(self, index, value, role):
        if index.column() == 2 and role == Qt.CheckStateRole:
            return QSqlTableModel.setData(self, index, QVariant('1' if value == Qt.Checked else '0'), Qt.EditRole)
        return QSqlTableModel.setData(self, index, value, role)


class TerminalConfig(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.ui = uic.loadUiType('terminal-config.ui')[0]()
        self.ui.setupUi(self)
        self.localize()

        self.model = TerminalSqlTableModel(self, QDB)
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.setTable('terminal')
        self.model.select()

        self.ui.terminals.setModel(self.model)
        self.ui.terminals.setColumnHidden(3, True)

        self.delegate = CenteredCheckBoxDelegate(self)
        self.ui.terminals.setItemDelegateForColumn(2, self.delegate)
        self.ui.terminals.horizontalHeader().setResizeMode(QHeaderView.Stretch)

        self.ui.ok.clicked.connect(self.edit_completed)
        self.ui.cancel.clicked.connect(self.cancel)
        self.ui.set_left.clicked.connect(self.set_left)
        self.ui.set_right.clicked.connect(self.set_right)

    def localize(self):
        self.setWindowTitle(_('Terminal config'))
        self.ui.ok.setText(_('OK'))
        self.ui.cancel.setText(_('Cancel'))

    def set_left(self):
        selected_indexes = self.ui.terminals.selectedIndexes()
        if selected_indexes:
            row = selected_indexes[0].row()
            self.model.set_option(row, 'left')

    def set_right(self):
        selected_indexes = self.ui.terminals.selectedIndexes()
        if selected_indexes:
            row = selected_indexes[0].row()
            self.model.set_option(row, 'right')

    def edit_completed(self):
        self.model.submitAll()
        self.accept()

    def cancel(self):
        self.reject()