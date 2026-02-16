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

class Ui_plot_dialog(object):
    def setupUi(self, plot_dialog):
        if not plot_dialog.objectName():
            plot_dialog.setObjectName(u"plot_dialog")
        plot_dialog.resize(1092, 732)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(plot_dialog.sizePolicy().hasHeightForWidth())
        plot_dialog.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QVBoxLayout(plot_dialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.profile_graphics_view = QGraphicsView(plot_dialog)
        self.profile_graphics_view.setObjectName(u"profile_graphics_view")

        self.verticalLayout_2.addWidget(self.profile_graphics_view)

        self.horizontal_layout = QHBoxLayout()
        self.horizontal_layout.setObjectName(u"horizontal_layout")
        self.save_profile_check_box = QCheckBox(plot_dialog)
        self.save_profile_check_box.setObjectName(u"save_profile_check_box")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.save_profile_check_box.setFont(font)

        self.horizontal_layout.addWidget(self.save_profile_check_box)

        self.dialog_button_box = QDialogButtonBox(plot_dialog)
        self.dialog_button_box.setObjectName(u"dialog_button_box")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.dialog_button_box.setFont(font1)
        self.dialog_button_box.setOrientation(Qt.Orientation.Horizontal)
        self.dialog_button_box.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.horizontal_layout.addWidget(self.dialog_button_box)


        self.verticalLayout_2.addLayout(self.horizontal_layout)


        self.retranslateUi(plot_dialog)
        self.dialog_button_box.rejected.connect(plot_dialog.reject)
        self.dialog_button_box.accepted.connect(plot_dialog.accept)

        QMetaObject.connectSlotsByName(plot_dialog)
    # setupUi

    def retranslateUi(self, plot_dialog):
        plot_dialog.setWindowTitle(QCoreApplication.translate("plot_dialog", u"PlotProfilesDialog", None))
        self.save_profile_check_box.setText(QCoreApplication.translate("plot_dialog", u"SAVE PROFILE", None))
    # retranslateUi

