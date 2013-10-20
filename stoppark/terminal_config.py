# -*- coding: utf-8 -*-
from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal, Qt, QVariant, QSize, QEvent
from PyQt4.QtGui import QDialog, QFont, QHeaderView, QStyledItemDelegate
from PyQt4.QtGui import QApplication, QStyle, QStyleOptionViewItem
from PyQt4.QtSql import QSqlDatabase, QSqlTableModel
import u2py.config


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

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            value = model.data(index, Qt.CheckStateRole)
            model.setData(index, value ^ Qt.Checked, Qt.CheckStateRole)
            return True
        return QStyledItemDelegate.editorEvent(self, event, model, option, index)


class TerminalSqlTableModel(QSqlTableModel):
    def __init__(self, parent=None, db=None):
        QSqlTableModel.__init__(self, parent, db)
        self.headers = [u'Адрес', u'Наименование', u'']

        self.font = QFont("Monospace", 18)

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

    def data(self, index, role):
        if role == Qt.FontRole:
            return self.font

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        if index.column() == 2:
            value = QSqlTableModel.data(self, index, Qt.EditRole).toInt()[0] == 1
            if role == Qt.CheckStateRole:
                return Qt.Checked if value else Qt.Unchecked
            if role == Qt.EditRole or role == Qt.DisplayRole:
                return QVariant(value)
            return QVariant()
        return QSqlTableModel.data(self, index, role)

    def setData(self, index, value, role):
        if index.column() == 2 and role == Qt.CheckStateRole:
            print 123
            return QSqlTableModel.setData(self, index, QVariant('1' if value == Qt.Checked else '0'), Qt.EditRole)
        return QSqlTableModel.setData(self, index, value, role)


class TerminalConfig(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.ui = uic.loadUiType('terminal-config.ui')[0]()
        self.ui.setupUi(self)

        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(u2py.config.db_filename)

        self.db.open()

        self.model = TerminalSqlTableModel(self, self.db)
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.setTable('terminal')
        self.model.select()

        self.ui.terminals.setModel(self.model)

        self.delegate = CenteredCheckBoxDelegate(self)
        self.ui.terminals.setItemDelegateForColumn(2, self.delegate)
        self.ui.terminals.horizontalHeader().setResizeMode(QHeaderView.Stretch)

        self.ui.ok.clicked.connect(self.edit_completed)

    def edit_completed(self):
        self.model.submitAll()
        self.db.commit()
        self.close()