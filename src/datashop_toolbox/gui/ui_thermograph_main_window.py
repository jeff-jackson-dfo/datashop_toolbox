# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'thermograph_gui.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialogButtonBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_thermograph_main_window(object):
    def setupUi(self, thermograph_main_window):
        if not thermograph_main_window.objectName():
            thermograph_main_window.setObjectName(u"thermograph_main_window")
        thermograph_main_window.resize(750, 380)
        self.centralwidget = QWidget(thermograph_main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_main = QVBoxLayout(self.centralwidget)
        self.verticalLayout_main.setObjectName(u"verticalLayout_main")
        self.name_vertical_layout = QVBoxLayout()
        self.name_vertical_layout.setObjectName(u"name_vertical_layout")
        self.name_label = QLabel(self.centralwidget)
        self.name_label.setObjectName(u"name_label")

        self.name_vertical_layout.addWidget(self.name_label)

        self.name_line_edit = QLineEdit(self.centralwidget)
        self.name_line_edit.setObjectName(u"name_line_edit")

        self.name_vertical_layout.addWidget(self.name_line_edit)


        self.verticalLayout_main.addLayout(self.name_vertical_layout)

        self.combos_horizontal_layout = QHBoxLayout()
        self.combos_horizontal_layout.setObjectName(u"combos_horizontal_layout")
        self.institution_vertical_layout = QVBoxLayout()
        self.institution_vertical_layout.setObjectName(u"institution_vertical_layout")
        self.institution_label = QLabel(self.centralwidget)
        self.institution_label.setObjectName(u"institution_label")

        self.institution_vertical_layout.addWidget(self.institution_label)

        self.institution_combo_box = QComboBox(self.centralwidget)
        self.institution_combo_box.addItem("")
        self.institution_combo_box.addItem("")
        self.institution_combo_box.addItem("")
        self.institution_combo_box.setObjectName(u"institution_combo_box")

        self.institution_vertical_layout.addWidget(self.institution_combo_box)


        self.combos_horizontal_layout.addLayout(self.institution_vertical_layout)

        self.instrument_vertical_layout = QVBoxLayout()
        self.instrument_vertical_layout.setObjectName(u"instrument_vertical_layout")
        self.instrument_label = QLabel(self.centralwidget)
        self.instrument_label.setObjectName(u"instrument_label")

        self.instrument_vertical_layout.addWidget(self.instrument_label)

        self.instrument_combo_box = QComboBox(self.centralwidget)
        self.instrument_combo_box.addItem("")
        self.instrument_combo_box.addItem("")
        self.instrument_combo_box.addItem("")
        self.instrument_combo_box.setObjectName(u"instrument_combo_box")

        self.instrument_vertical_layout.addWidget(self.instrument_combo_box)


        self.combos_horizontal_layout.addLayout(self.instrument_vertical_layout)


        self.verticalLayout_main.addLayout(self.combos_horizontal_layout)

        self.buttons_horizontal_layout = QHBoxLayout()
        self.buttons_horizontal_layout.setObjectName(u"buttons_horizontal_layout")
        self.metadata_push_button = QPushButton(self.centralwidget)
        self.metadata_push_button.setObjectName(u"metadata_push_button")

        self.buttons_horizontal_layout.addWidget(self.metadata_push_button)

        self.data_folder_push_button = QPushButton(self.centralwidget)
        self.data_folder_push_button.setObjectName(u"data_folder_push_button")

        self.buttons_horizontal_layout.addWidget(self.data_folder_push_button)


        self.verticalLayout_main.addLayout(self.buttons_horizontal_layout)

        self.metadata_horizontal_layout = QHBoxLayout()
        self.metadata_horizontal_layout.setObjectName(u"metadata_horizontal_layout")
        self.metadata_label = QLabel(self.centralwidget)
        self.metadata_label.setObjectName(u"metadata_label")

        self.metadata_horizontal_layout.addWidget(self.metadata_label)

        self.metadata_line_edit = QLineEdit(self.centralwidget)
        self.metadata_line_edit.setObjectName(u"metadata_line_edit")

        self.metadata_horizontal_layout.addWidget(self.metadata_line_edit)


        self.verticalLayout_main.addLayout(self.metadata_horizontal_layout)

        self.data_folder_horizontal_layout = QHBoxLayout()
        self.data_folder_horizontal_layout.setObjectName(u"data_folder_horizontal_layout")
        self.data_folder_label = QLabel(self.centralwidget)
        self.data_folder_label.setObjectName(u"data_folder_label")

        self.data_folder_horizontal_layout.addWidget(self.data_folder_label)

        self.data_folder_line_edit = QLineEdit(self.centralwidget)
        self.data_folder_line_edit.setObjectName(u"data_folder_line_edit")

        self.data_folder_horizontal_layout.addWidget(self.data_folder_line_edit)


        self.verticalLayout_main.addLayout(self.data_folder_horizontal_layout)

        self.ok_cancel_horizontal_layout = QHBoxLayout()
        self.ok_cancel_horizontal_layout.setObjectName(u"ok_cancel_horizontal_layout")
        self.lef_horizontal_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.ok_cancel_horizontal_layout.addItem(self.lef_horizontal_spacer)

        self.dialog_button_box = QDialogButtonBox(self.centralwidget)
        self.dialog_button_box.setObjectName(u"dialog_button_box")
        self.dialog_button_box.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.ok_cancel_horizontal_layout.addWidget(self.dialog_button_box)

        self.right_horizontal_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.ok_cancel_horizontal_layout.addItem(self.right_horizontal_spacer)


        self.verticalLayout_main.addLayout(self.ok_cancel_horizontal_layout)

        thermograph_main_window.setCentralWidget(self.centralwidget)

        self.retranslateUi(thermograph_main_window)

        QMetaObject.connectSlotsByName(thermograph_main_window)
    # setupUi

    def retranslateUi(self, thermograph_main_window):
        thermograph_main_window.setWindowTitle(QCoreApplication.translate("thermograph_main_window", u"Choose Moored Thermograph Files to Process", None))
        self.name_label.setText(QCoreApplication.translate("thermograph_main_window", u"Please enter the data processor's name in the text box below:", None))
        self.institution_label.setText(QCoreApplication.translate("thermograph_main_window", u"Select institution:", None))
        self.institution_combo_box.setItemText(0, QCoreApplication.translate("thermograph_main_window", u"Unknown", None))
        self.institution_combo_box.setItemText(1, QCoreApplication.translate("thermograph_main_window", u"BIO", None))
        self.institution_combo_box.setItemText(2, QCoreApplication.translate("thermograph_main_window", u"FSRS", None))

        self.instrument_label.setText(QCoreApplication.translate("thermograph_main_window", u"Select instrument:", None))
        self.instrument_combo_box.setItemText(0, QCoreApplication.translate("thermograph_main_window", u"Unknown", None))
        self.instrument_combo_box.setItemText(1, QCoreApplication.translate("thermograph_main_window", u"Minilog", None))
        self.instrument_combo_box.setItemText(2, QCoreApplication.translate("thermograph_main_window", u"Hobo", None))

        self.metadata_push_button.setText(QCoreApplication.translate("thermograph_main_window", u"Select the Metadata file\n"
"(e.g. LFA .txt or Excel file)", None))
        self.data_folder_push_button.setText(QCoreApplication.translate("thermograph_main_window", u"Select the Data folder\n"
"(Location of *.csv files)", None))
        self.metadata_label.setText(QCoreApplication.translate("thermograph_main_window", u"Metadata file selected:", None))
        self.data_folder_label.setText(QCoreApplication.translate("thermograph_main_window", u"Data folder selected:", None))
    # retranslateUi

