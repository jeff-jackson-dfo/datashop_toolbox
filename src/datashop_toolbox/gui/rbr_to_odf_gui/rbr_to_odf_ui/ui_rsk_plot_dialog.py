# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rsk_plot_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QGraphicsView, QHBoxLayout, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_PlotDialog(object):
    def setupUi(self, PlotDialog):
        if not PlotDialog.objectName():
            PlotDialog.setObjectName(u"PlotDialog")
        PlotDialog.resize(1092, 732)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(PlotDialog.sizePolicy().hasHeightForWidth())
        PlotDialog.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QVBoxLayout(PlotDialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.profileGraphicsView = QGraphicsView(PlotDialog)
        self.profileGraphicsView.setObjectName(u"profileGraphicsView")

        self.verticalLayout_2.addWidget(self.profileGraphicsView)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.saveProfileCheckBox = QCheckBox(PlotDialog)
        self.saveProfileCheckBox.setObjectName(u"saveProfileCheckBox")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.saveProfileCheckBox.setFont(font)

        self.horizontalLayout.addWidget(self.saveProfileCheckBox)

        self.buttonBox = QDialogButtonBox(PlotDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.buttonBox.setFont(font1)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.horizontalLayout.addWidget(self.buttonBox)


        self.verticalLayout_2.addLayout(self.horizontalLayout)


        self.retranslateUi(PlotDialog)
        self.buttonBox.rejected.connect(PlotDialog.reject)
        self.buttonBox.accepted.connect(PlotDialog.accept)

        QMetaObject.connectSlotsByName(PlotDialog)
    # setupUi

    def retranslateUi(self, PlotDialog):
        PlotDialog.setWindowTitle(QCoreApplication.translate("PlotDialog", u"PlotProfilesDialog", None))
        self.saveProfileCheckBox.setText(QCoreApplication.translate("PlotDialog", u"SAVE PROFILE", None))
    # retranslateUi

