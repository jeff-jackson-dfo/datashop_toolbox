# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rbr_to_odf.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QSpacerItem,
    QStatusBar, QVBoxLayout, QWidget)

class Ui_main_window(object):
    def setupUi(self, main_window):
        if not main_window.objectName():
            main_window.setObjectName(u"main_window")
        main_window.resize(980, 850)
        self.centralwidget = QWidget(main_window)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.vertical_spacer_10 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.vertical_spacer_10, 2, 0, 1, 1)

        self.vertical_layout_2 = QVBoxLayout()
        self.vertical_layout_2.setObjectName(u"vertical_layout_2")
        self.vertical_spacer_8 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout_2.addItem(self.vertical_spacer_8)

        self.horizontal_layout = QHBoxLayout()
        self.horizontal_layout.setObjectName(u"horizontal_layout")
        self.latitude_label = QLabel(self.centralwidget)
        self.latitude_label.setObjectName(u"latitude_label")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(11)
        font.setBold(True)
        self.latitude_label.setFont(font)

        self.horizontal_layout.addWidget(self.latitude_label)

        self.latitude_line_edit = QLineEdit(self.centralwidget)
        self.latitude_line_edit.setObjectName(u"latitude_line_edit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.latitude_line_edit.sizePolicy().hasHeightForWidth())
        self.latitude_line_edit.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.latitude_line_edit.setFont(font1)
        self.latitude_line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontal_layout.addWidget(self.latitude_line_edit)


        self.vertical_layout_2.addLayout(self.horizontal_layout)

        self.horizontal_layout_2 = QHBoxLayout()
        self.horizontal_layout_2.setObjectName(u"horizontal_layout_2")
        self.longitude_label = QLabel(self.centralwidget)
        self.longitude_label.setObjectName(u"longitude_label")
        self.longitude_label.setFont(font)

        self.horizontal_layout_2.addWidget(self.longitude_label)

        self.longitude_line_edit = QLineEdit(self.centralwidget)
        self.longitude_line_edit.setObjectName(u"longitude_line_edit")
        sizePolicy.setHeightForWidth(self.longitude_line_edit.sizePolicy().hasHeightForWidth())
        self.longitude_line_edit.setSizePolicy(sizePolicy)
        self.longitude_line_edit.setFont(font1)
        self.longitude_line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontal_layout_2.addWidget(self.longitude_line_edit)


        self.vertical_layout_2.addLayout(self.horizontal_layout_2)

        self.vertical_spacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout_2.addItem(self.vertical_spacer_2)

        self.vertical_layout = QVBoxLayout()
        self.vertical_layout.setObjectName(u"vertical_layout")
        self.profile_plots_push_button = QPushButton(self.centralwidget)
        self.profile_plots_push_button.setObjectName(u"profile_plots_push_button")
        font2 = QFont()
        font2.setPointSize(10)
        font2.setBold(True)
        self.profile_plots_push_button.setFont(font2)

        self.vertical_layout.addWidget(self.profile_plots_push_button)

        self.vertical_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout.addItem(self.vertical_spacer)

        self.clear_info_push_button = QPushButton(self.centralwidget)
        self.clear_info_push_button.setObjectName(u"clear_info_push_button")
        self.clear_info_push_button.setFont(font2)

        self.vertical_layout.addWidget(self.clear_info_push_button)

        self.vertical_spacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout.addItem(self.vertical_spacer_3)

        self.edit_metadata_push_button = QPushButton(self.centralwidget)
        self.edit_metadata_push_button.setObjectName(u"edit_metadata_push_button")
        self.edit_metadata_push_button.setFont(font2)

        self.vertical_layout.addWidget(self.edit_metadata_push_button)

        self.vertical_spacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout.addItem(self.vertical_spacer_4)

        self.export_odf_push_button = QPushButton(self.centralwidget)
        self.export_odf_push_button.setObjectName(u"export_odf_push_button")
        self.export_odf_push_button.setFont(font2)

        self.vertical_layout.addWidget(self.export_odf_push_button)

        self.vertical_spacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout.addItem(self.vertical_spacer_5)

        self.vertical_spacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout.addItem(self.vertical_spacer_6)

        self.vertical_spacer_7 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.vertical_layout.addItem(self.vertical_spacer_7)


        self.vertical_layout_2.addLayout(self.vertical_layout)


        self.gridLayout_2.addLayout(self.vertical_layout_2, 5, 2, 1, 1)

        self.horizontal_layout_3 = QHBoxLayout()
        self.horizontal_layout_3.setObjectName(u"horizontal_layout_3")
        self.select_folder_push_button = QPushButton(self.centralwidget)
        self.select_folder_push_button.setObjectName(u"select_folder_push_button")
        self.select_folder_push_button.setFont(font2)

        self.horizontal_layout_3.addWidget(self.select_folder_push_button)

        self.folder_line_edit = QLineEdit(self.centralwidget)
        self.folder_line_edit.setObjectName(u"folder_line_edit")
        self.folder_line_edit.setFont(font2)
        self.folder_line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.folder_line_edit.setReadOnly(True)

        self.horizontal_layout_3.addWidget(self.folder_line_edit)


        self.gridLayout_2.addLayout(self.horizontal_layout_3, 3, 0, 1, 3)

        self.vertical_spacer_9 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.vertical_spacer_9, 4, 0, 1, 1)

        self.vertical_layout_4 = QVBoxLayout()
        self.vertical_layout_4.setObjectName(u"vertical_layout_4")
        self.channel_list_label = QLabel(self.centralwidget)
        self.channel_list_label.setObjectName(u"channel_list_label")
        self.channel_list_label.setFont(font1)
        self.channel_list_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vertical_layout_4.addWidget(self.channel_list_label)

        self.channel_list_widget = QListWidget(self.centralwidget)
        self.channel_list_widget.setObjectName(u"channel_list_widget")
        font3 = QFont()
        font3.setPointSize(9)
        font3.setBold(True)
        self.channel_list_widget.setFont(font3)
        self.channel_list_widget.setSortingEnabled(True)

        self.vertical_layout_4.addWidget(self.channel_list_widget)


        self.gridLayout_2.addLayout(self.vertical_layout_4, 5, 1, 1, 1)

        self.grid_layout = QGridLayout()
        self.grid_layout.setObjectName(u"grid_layout")
        self.odf_folder_line_edit = QLineEdit(self.centralwidget)
        self.odf_folder_line_edit.setObjectName(u"odf_folder_line_edit")
        self.odf_folder_line_edit.setFont(font2)
        self.odf_folder_line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.odf_folder_line_edit.setReadOnly(True)

        self.grid_layout.addWidget(self.odf_folder_line_edit, 0, 0, 1, 1)

        self.exit_push_button = QPushButton(self.centralwidget)
        self.exit_push_button.setObjectName(u"exit_push_button")
        sizePolicy.setHeightForWidth(self.exit_push_button.sizePolicy().hasHeightForWidth())
        self.exit_push_button.setSizePolicy(sizePolicy)
        font4 = QFont()
        font4.setPointSize(18)
        font4.setBold(True)
        self.exit_push_button.setFont(font4)

        self.grid_layout.addWidget(self.exit_push_button, 1, 0, 1, 1, Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignVCenter)


        self.gridLayout_2.addLayout(self.grid_layout, 7, 0, 1, 3)

        self.vertical_spacer_11 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.vertical_spacer_11, 6, 0, 1, 1)

        self.title_label = QLabel(self.centralwidget)
        self.title_label.setObjectName(u"title_label")
        font5 = QFont()
        font5.setPointSize(20)
        font5.setBold(True)
        self.title_label.setFont(font5)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.title_label, 1, 0, 1, 3)

        self.vertical_layout_3 = QVBoxLayout()
        self.vertical_layout_3.setObjectName(u"vertical_layout_3")
        self.rsk_list_label = QLabel(self.centralwidget)
        self.rsk_list_label.setObjectName(u"rsk_list_label")
        self.rsk_list_label.setFont(font1)
        self.rsk_list_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vertical_layout_3.addWidget(self.rsk_list_label)

        self.rsk_list_widget = QListWidget(self.centralwidget)
        self.rsk_list_widget.setObjectName(u"rsk_list_widget")
        self.rsk_list_widget.setFont(font3)
        self.rsk_list_widget.setSortingEnabled(True)

        self.vertical_layout_3.addWidget(self.rsk_list_widget)


        self.gridLayout_2.addLayout(self.vertical_layout_3, 5, 0, 1, 1)

        self.vertical_spacer_12 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.vertical_spacer_12, 0, 0, 1, 1)

        main_window.setCentralWidget(self.centralwidget)
        self.menu_bar = QMenuBar(main_window)
        self.menu_bar.setObjectName(u"menu_bar")
        self.menu_bar.setGeometry(QRect(0, 0, 980, 22))
        main_window.setMenuBar(self.menu_bar)
        self.status_bar = QStatusBar(main_window)
        self.status_bar.setObjectName(u"status_bar")
        main_window.setStatusBar(self.status_bar)

        self.retranslateUi(main_window)

        QMetaObject.connectSlotsByName(main_window)
    # setupUi

    def retranslateUi(self, main_window):
        main_window.setWindowTitle(QCoreApplication.translate("main_window", u"RSK to ODF Conversion Application", None))
        self.latitude_label.setText(QCoreApplication.translate("main_window", u"Station Latitude:", None))
        self.longitude_label.setText(QCoreApplication.translate("main_window", u"Station Longitude:", None))
        self.profile_plots_push_button.setText(QCoreApplication.translate("main_window", u"DISPLAY PROFILES FOR SELECTED FILE", None))
        self.clear_info_push_button.setText(QCoreApplication.translate("main_window", u"CLEAR IMPORTED RSK INFO", None))
        self.edit_metadata_push_button.setText(QCoreApplication.translate("main_window", u"EDIT ODF METADATA", None))
        self.export_odf_push_button.setText(QCoreApplication.translate("main_window", u"EXPORT TO ODF", None))
        self.select_folder_push_button.setText(QCoreApplication.translate("main_window", u"Select Folder with .RSK files", None))
        self.folder_line_edit.setText(QCoreApplication.translate("main_window", u"Full folder path to .rsk files to be converted ...", None))
        self.channel_list_label.setText(QCoreApplication.translate("main_window", u"Channels found in loaded RSK File", None))
        self.odf_folder_line_edit.setText(QCoreApplication.translate("main_window", u"Full folder path to where .odf file will be exported ...", None))
        self.exit_push_button.setText(QCoreApplication.translate("main_window", u"EXIT", None))
        self.title_label.setText(QCoreApplication.translate("main_window", u"Conversion of RBR Ruskin (.rsk) file(s) to ODF file(s)", None))
        self.rsk_list_label.setText(QCoreApplication.translate("main_window", u"RSK Files Found in Selected Folder", None))
    # retranslateUi

