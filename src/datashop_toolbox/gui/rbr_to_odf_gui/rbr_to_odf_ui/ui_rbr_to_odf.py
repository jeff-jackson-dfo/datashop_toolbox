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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(980, 850)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout_2 = QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.verticalSpacer_10 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_10, 2, 0, 1, 1)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalSpacer_8 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_8)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.latitudeLabel = QLabel(self.centralwidget)
        self.latitudeLabel.setObjectName(u"latitudeLabel")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(11)
        font.setBold(True)
        self.latitudeLabel.setFont(font)

        self.horizontalLayout.addWidget(self.latitudeLabel)

        self.latitudeLineEdit = QLineEdit(self.centralwidget)
        self.latitudeLineEdit.setObjectName(u"latitudeLineEdit")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.latitudeLineEdit.sizePolicy().hasHeightForWidth())
        self.latitudeLineEdit.setSizePolicy(sizePolicy)
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.latitudeLineEdit.setFont(font1)
        self.latitudeLineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.latitudeLineEdit)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.longitudeLabel = QLabel(self.centralwidget)
        self.longitudeLabel.setObjectName(u"longitudeLabel")
        self.longitudeLabel.setFont(font)

        self.horizontalLayout_2.addWidget(self.longitudeLabel)

        self.longitudeLineEdit = QLineEdit(self.centralwidget)
        self.longitudeLineEdit.setObjectName(u"longitudeLineEdit")
        sizePolicy.setHeightForWidth(self.longitudeLineEdit.sizePolicy().hasHeightForWidth())
        self.longitudeLineEdit.setSizePolicy(sizePolicy)
        self.longitudeLineEdit.setFont(font1)
        self.longitudeLineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_2.addWidget(self.longitudeLineEdit)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.profilePlotsButton = QPushButton(self.centralwidget)
        self.profilePlotsButton.setObjectName(u"profilePlotsButton")
        font2 = QFont()
        font2.setPointSize(10)
        font2.setBold(True)
        self.profilePlotsButton.setFont(font2)

        self.verticalLayout.addWidget(self.profilePlotsButton)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.clearInfoPushButton = QPushButton(self.centralwidget)
        self.clearInfoPushButton.setObjectName(u"clearInfoPushButton")
        self.clearInfoPushButton.setFont(font2)

        self.verticalLayout.addWidget(self.clearInfoPushButton)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_3)

        self.editMetadataPushButton = QPushButton(self.centralwidget)
        self.editMetadataPushButton.setObjectName(u"editMetadataPushButton")
        self.editMetadataPushButton.setFont(font2)

        self.verticalLayout.addWidget(self.editMetadataPushButton)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_4)

        self.exportOdfPushButton = QPushButton(self.centralwidget)
        self.exportOdfPushButton.setObjectName(u"exportOdfPushButton")
        self.exportOdfPushButton.setFont(font2)

        self.verticalLayout.addWidget(self.exportOdfPushButton)

        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_5)

        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_6)

        self.verticalSpacer_7 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_7)


        self.verticalLayout_2.addLayout(self.verticalLayout)


        self.gridLayout_2.addLayout(self.verticalLayout_2, 5, 2, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.selectFolderButton = QPushButton(self.centralwidget)
        self.selectFolderButton.setObjectName(u"selectFolderButton")
        self.selectFolderButton.setFont(font2)

        self.horizontalLayout_3.addWidget(self.selectFolderButton)

        self.folderLineEdit = QLineEdit(self.centralwidget)
        self.folderLineEdit.setObjectName(u"folderLineEdit")
        self.folderLineEdit.setFont(font2)
        self.folderLineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.folderLineEdit.setReadOnly(True)

        self.horizontalLayout_3.addWidget(self.folderLineEdit)


        self.gridLayout_2.addLayout(self.horizontalLayout_3, 3, 0, 1, 3)

        self.verticalSpacer_9 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_9, 4, 0, 1, 1)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.channelListLabel = QLabel(self.centralwidget)
        self.channelListLabel.setObjectName(u"channelListLabel")
        self.channelListLabel.setFont(font1)
        self.channelListLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_4.addWidget(self.channelListLabel)

        self.channelListWidget = QListWidget(self.centralwidget)
        self.channelListWidget.setObjectName(u"channelListWidget")
        font3 = QFont()
        font3.setPointSize(9)
        font3.setBold(True)
        self.channelListWidget.setFont(font3)
        self.channelListWidget.setSortingEnabled(True)

        self.verticalLayout_4.addWidget(self.channelListWidget)


        self.gridLayout_2.addLayout(self.verticalLayout_4, 5, 1, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.odfFolderLineEdit = QLineEdit(self.centralwidget)
        self.odfFolderLineEdit.setObjectName(u"odfFolderLineEdit")
        self.odfFolderLineEdit.setFont(font2)
        self.odfFolderLineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.odfFolderLineEdit.setReadOnly(True)

        self.gridLayout.addWidget(self.odfFolderLineEdit, 0, 0, 1, 1)

        self.exitPushButton = QPushButton(self.centralwidget)
        self.exitPushButton.setObjectName(u"exitPushButton")
        sizePolicy.setHeightForWidth(self.exitPushButton.sizePolicy().hasHeightForWidth())
        self.exitPushButton.setSizePolicy(sizePolicy)
        font4 = QFont()
        font4.setPointSize(18)
        font4.setBold(True)
        self.exitPushButton.setFont(font4)

        self.gridLayout.addWidget(self.exitPushButton, 1, 0, 1, 1, Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignVCenter)


        self.gridLayout_2.addLayout(self.gridLayout, 7, 0, 1, 3)

        self.verticalSpacer_11 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_11, 6, 0, 1, 1)

        self.titleLabel = QLabel(self.centralwidget)
        self.titleLabel.setObjectName(u"titleLabel")
        font5 = QFont()
        font5.setPointSize(20)
        font5.setBold(True)
        self.titleLabel.setFont(font5)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_2.addWidget(self.titleLabel, 1, 0, 1, 3)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.rskListLabel = QLabel(self.centralwidget)
        self.rskListLabel.setObjectName(u"rskListLabel")
        self.rskListLabel.setFont(font1)
        self.rskListLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.rskListLabel)

        self.rskListWidget = QListWidget(self.centralwidget)
        self.rskListWidget.setObjectName(u"rskListWidget")
        self.rskListWidget.setFont(font3)
        self.rskListWidget.setSortingEnabled(True)

        self.verticalLayout_3.addWidget(self.rskListWidget)


        self.gridLayout_2.addLayout(self.verticalLayout_3, 5, 0, 1, 1)

        self.verticalSpacer_12 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_12, 0, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 980, 22))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"RSK to ODF Conversion Application", None))
        self.latitudeLabel.setText(QCoreApplication.translate("MainWindow", u"Station Latitude:", None))
        self.longitudeLabel.setText(QCoreApplication.translate("MainWindow", u"Station Longitude:", None))
        self.profilePlotsButton.setText(QCoreApplication.translate("MainWindow", u"DISPLAY PROFILES FOR SELECTED FILE", None))
        self.clearInfoPushButton.setText(QCoreApplication.translate("MainWindow", u"CLEAR IMPORTED RSK INFO", None))
        self.editMetadataPushButton.setText(QCoreApplication.translate("MainWindow", u"EDIT ODF METADATA", None))
        self.exportOdfPushButton.setText(QCoreApplication.translate("MainWindow", u"EXPORT TO ODF", None))
        self.selectFolderButton.setText(QCoreApplication.translate("MainWindow", u"Select Folder with .RSK files", None))
        self.folderLineEdit.setText(QCoreApplication.translate("MainWindow", u"Full folder path to .rsk files to be converted ...", None))
        self.channelListLabel.setText(QCoreApplication.translate("MainWindow", u"Channels found in loaded RSK File", None))
        self.odfFolderLineEdit.setText(QCoreApplication.translate("MainWindow", u"Full folder path to where .odf file will be exported ...", None))
        self.exitPushButton.setText(QCoreApplication.translate("MainWindow", u"EXIT", None))
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"Conversion of RBR Ruskin (.rsk) file(s) to ODF file(s)", None))
        self.rskListLabel.setText(QCoreApplication.translate("MainWindow", u"RSK Files Found in Selected Folder", None))
    # retranslateUi

