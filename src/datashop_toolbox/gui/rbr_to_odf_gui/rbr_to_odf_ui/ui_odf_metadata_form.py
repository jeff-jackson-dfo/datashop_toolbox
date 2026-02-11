# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'odf_metadata_form.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QWidget)

class Ui_ODF_Metadata_Form(object):
    def setupUi(self, ODF_Metadata_Form):
        if not ODF_Metadata_Form.objectName():
            ODF_Metadata_Form.setObjectName(u"ODF_Metadata_Form")
        ODF_Metadata_Form.setWindowModality(Qt.WindowModality.NonModal)
        ODF_Metadata_Form.resize(1100, 822)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(ODF_Metadata_Form.sizePolicy().hasHeightForWidth())
        ODF_Metadata_Form.setSizePolicy(sizePolicy)
        self.missionTemplateSelectorComboBox = QComboBox(ODF_Metadata_Form)
        self.missionTemplateSelectorComboBox.setObjectName(u"missionTemplateSelectorComboBox")
        self.missionTemplateSelectorComboBox.setGeometry(QRect(270, 20, 311, 22))
        font = QFont()
        font.setPointSize(9)
        self.missionTemplateSelectorComboBox.setFont(font)
        self.okPushButton = QPushButton(ODF_Metadata_Form)
        self.okPushButton.setObjectName(u"okPushButton")
        self.okPushButton.setGeometry(QRect(310, 730, 201, 61))
        font1 = QFont()
        font1.setPointSize(16)
        font1.setBold(True)
        font1.setKerning(True)
        self.okPushButton.setFont(font1)
        self.okPushButton.setAutoFillBackground(False)
        self.missionTemplateSelectorLabel = QLabel(ODF_Metadata_Form)
        self.missionTemplateSelectorLabel.setObjectName(u"missionTemplateSelectorLabel")
        self.missionTemplateSelectorLabel.setGeometry(QRect(30, 10, 231, 39))
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.missionTemplateSelectorLabel.setFont(font2)
        self.cruiseHeaderGoupBox = QGroupBox(ODF_Metadata_Form)
        self.cruiseHeaderGoupBox.setObjectName(u"cruiseHeaderGoupBox")
        self.cruiseHeaderGoupBox.setGeometry(QRect(20, 110, 491, 282))
        self.gridLayout_2 = QGridLayout(self.cruiseHeaderGoupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.cruiseNumberLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.cruiseNumberLineEdit.setObjectName(u"cruiseNumberLineEdit")
        self.cruiseNumberLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.cruiseNumberLineEdit, 1, 4, 1, 3)

        self.countryInstituteCodeLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.countryInstituteCodeLineEdit.setObjectName(u"countryInstituteCodeLineEdit")
        self.countryInstituteCodeLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.countryInstituteCodeLineEdit, 0, 6, 1, 1)

        self.platformLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.platformLineEdit.setObjectName(u"platformLineEdit")
        self.platformLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.platformLineEdit, 6, 2, 1, 5)

        self.cruiseDesciptionLabel = QLabel(self.cruiseHeaderGoupBox)
        self.cruiseDesciptionLabel.setObjectName(u"cruiseDesciptionLabel")

        self.gridLayout_2.addWidget(self.cruiseDesciptionLabel, 8, 0, 1, 5)

        self.endDateLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.endDateLineEdit.setObjectName(u"endDateLineEdit")
        self.endDateLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.endDateLineEdit, 5, 1, 1, 6)

        self.countryInstituteCodeLabel = QLabel(self.cruiseHeaderGoupBox)
        self.countryInstituteCodeLabel.setObjectName(u"countryInstituteCodeLabel")

        self.gridLayout_2.addWidget(self.countryInstituteCodeLabel, 0, 0, 1, 6)

        self.chiefScientistLabel = QLabel(self.cruiseHeaderGoupBox)
        self.chiefScientistLabel.setObjectName(u"chiefScientistLabel")

        self.gridLayout_2.addWidget(self.chiefScientistLabel, 3, 0, 1, 4)

        self.organizationLabel = QLabel(self.cruiseHeaderGoupBox)
        self.organizationLabel.setObjectName(u"organizationLabel")

        self.gridLayout_2.addWidget(self.organizationLabel, 2, 0, 1, 4)

        self.platformLabel = QLabel(self.cruiseHeaderGoupBox)
        self.platformLabel.setObjectName(u"platformLabel")

        self.gridLayout_2.addWidget(self.platformLabel, 6, 0, 1, 1)

        self.organizationLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.organizationLineEdit.setObjectName(u"organizationLineEdit")
        self.organizationLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.organizationLineEdit, 2, 4, 1, 3)

        self.cruiseNumberLabel = QLabel(self.cruiseHeaderGoupBox)
        self.cruiseNumberLabel.setObjectName(u"cruiseNumberLabel")

        self.gridLayout_2.addWidget(self.cruiseNumberLabel, 1, 0, 1, 4)

        self.startDateLabel = QLabel(self.cruiseHeaderGoupBox)
        self.startDateLabel.setObjectName(u"startDateLabel")

        self.gridLayout_2.addWidget(self.startDateLabel, 4, 0, 1, 2)

        self.startDateLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.startDateLineEdit.setObjectName(u"startDateLineEdit")
        self.startDateLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.startDateLineEdit, 4, 2, 1, 5)

        self.cruiseDescriptionLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.cruiseDescriptionLineEdit.setObjectName(u"cruiseDescriptionLineEdit")
        self.cruiseDescriptionLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.cruiseDescriptionLineEdit, 8, 5, 1, 2)

        self.cruiseNameLabel = QLabel(self.cruiseHeaderGoupBox)
        self.cruiseNameLabel.setObjectName(u"cruiseNameLabel")

        self.gridLayout_2.addWidget(self.cruiseNameLabel, 7, 0, 1, 3)

        self.chiefScientistLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.chiefScientistLineEdit.setObjectName(u"chiefScientistLineEdit")
        self.chiefScientistLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.chiefScientistLineEdit, 3, 4, 1, 3)

        self.endDateLabel = QLabel(self.cruiseHeaderGoupBox)
        self.endDateLabel.setObjectName(u"endDateLabel")

        self.gridLayout_2.addWidget(self.endDateLabel, 5, 0, 1, 1)

        self.cruiseNameLineEdit = QLineEdit(self.cruiseHeaderGoupBox)
        self.cruiseNameLineEdit.setObjectName(u"cruiseNameLineEdit")
        self.cruiseNameLineEdit.setFont(font)

        self.gridLayout_2.addWidget(self.cruiseNameLineEdit, 7, 3, 1, 4)

        self.cancelPushButton = QPushButton(ODF_Metadata_Form)
        self.cancelPushButton.setObjectName(u"cancelPushButton")
        self.cancelPushButton.setGeometry(QRect(520, 730, 201, 61))
        self.cancelPushButton.setFont(font1)
        self.cancelPushButton.setAutoFillBackground(False)
        self.eventHeaderGroupBox = QGroupBox(ODF_Metadata_Form)
        self.eventHeaderGroupBox.setObjectName(u"eventHeaderGroupBox")
        self.eventHeaderGroupBox.setGeometry(QRect(520, 110, 521, 590))
        self.gridLayout_3 = QGridLayout(self.eventHeaderGroupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.minDepthLabel = QLabel(self.eventHeaderGroupBox)
        self.minDepthLabel.setObjectName(u"minDepthLabel")

        self.gridLayout_3.addWidget(self.minDepthLabel, 12, 0, 1, 1)

        self.stationNameLabel = QLabel(self.eventHeaderGroupBox)
        self.stationNameLabel.setObjectName(u"stationNameLabel")

        self.gridLayout_3.addWidget(self.stationNameLabel, 17, 0, 1, 5)

        self.eventNumberLabel = QLabel(self.eventHeaderGroupBox)
        self.eventNumberLabel.setObjectName(u"eventNumberLabel")

        self.gridLayout_3.addWidget(self.eventNumberLabel, 1, 0, 1, 6)

        self.eventQualifier2Label = QLabel(self.eventHeaderGroupBox)
        self.eventQualifier2Label.setObjectName(u"eventQualifier2Label")

        self.gridLayout_3.addWidget(self.eventQualifier2Label, 3, 0, 1, 9)

        self.endLatitudeLabel = QLabel(self.eventHeaderGroupBox)
        self.endLatitudeLabel.setObjectName(u"endLatitudeLabel")

        self.gridLayout_3.addWidget(self.endLatitudeLabel, 10, 0, 1, 4)

        self.soundingLabel = QLabel(self.eventHeaderGroupBox)
        self.soundingLabel.setObjectName(u"soundingLabel")

        self.gridLayout_3.addWidget(self.soundingLabel, 15, 0, 1, 1)

        self.origCreationDateLabel = QLabel(self.eventHeaderGroupBox)
        self.origCreationDateLabel.setObjectName(u"origCreationDateLabel")

        self.gridLayout_3.addWidget(self.origCreationDateLabel, 5, 0, 1, 12)

        self.dataTypeLabel = QLabel(self.eventHeaderGroupBox)
        self.dataTypeLabel.setObjectName(u"dataTypeLabel")

        self.gridLayout_3.addWidget(self.dataTypeLabel, 0, 0, 1, 1)

        self.initialLongitudeLabel = QLabel(self.eventHeaderGroupBox)
        self.initialLongitudeLabel.setObjectName(u"initialLongitudeLabel")

        self.gridLayout_3.addWidget(self.initialLongitudeLabel, 9, 0, 1, 10)

        self.endDateTimeLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.endDateTimeLineEdit.setObjectName(u"endDateTimeLineEdit")
        self.endDateTimeLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.endDateTimeLineEdit, 7, 7, 1, 6)

        self.eventCommentsLabel = QLabel(self.eventHeaderGroupBox)
        self.eventCommentsLabel.setObjectName(u"eventCommentsLabel")

        self.gridLayout_3.addWidget(self.eventCommentsLabel, 19, 0, 1, 10)

        self.initialLatitudeLabel = QLabel(self.eventHeaderGroupBox)
        self.initialLatitudeLabel.setObjectName(u"initialLatitudeLabel")

        self.gridLayout_3.addWidget(self.initialLatitudeLabel, 8, 0, 1, 7)

        self.initialLatitudeLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.initialLatitudeLineEdit.setObjectName(u"initialLatitudeLineEdit")
        self.initialLatitudeLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.initialLatitudeLineEdit, 8, 8, 1, 5)

        self.setNumberLabel = QLabel(self.eventHeaderGroupBox)
        self.setNumberLabel.setObjectName(u"setNumberLabel")

        self.gridLayout_3.addWidget(self.setNumberLabel, 18, 0, 1, 3)

        self.eventCommentsLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.eventCommentsLineEdit.setObjectName(u"eventCommentsLineEdit")
        self.eventCommentsLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.eventCommentsLineEdit, 19, 10, 1, 3)

        self.eventQualifier1Label = QLabel(self.eventHeaderGroupBox)
        self.eventQualifier1Label.setObjectName(u"eventQualifier1Label")

        self.gridLayout_3.addWidget(self.eventQualifier1Label, 2, 0, 1, 9)

        self.maxDepthLabel = QLabel(self.eventHeaderGroupBox)
        self.maxDepthLabel.setObjectName(u"maxDepthLabel")

        self.gridLayout_3.addWidget(self.maxDepthLabel, 13, 0, 1, 2)

        self.samplingIntervalLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.samplingIntervalLineEdit.setObjectName(u"samplingIntervalLineEdit")
        self.samplingIntervalLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.samplingIntervalLineEdit, 14, 12, 1, 1)

        self.endLongitudeLabel = QLabel(self.eventHeaderGroupBox)
        self.endLongitudeLabel.setObjectName(u"endLongitudeLabel")

        self.gridLayout_3.addWidget(self.endLongitudeLabel, 11, 0, 1, 6)

        self.setNumberLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.setNumberLineEdit.setObjectName(u"setNumberLineEdit")
        self.setNumberLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.setNumberLineEdit, 18, 4, 1, 9)

        self.endLatitudeLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.endLatitudeLineEdit.setObjectName(u"endLatitudeLineEdit")
        self.endLatitudeLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.endLatitudeLineEdit, 10, 5, 1, 8)

        self.eventQualifier2LineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.eventQualifier2LineEdit.setObjectName(u"eventQualifier2LineEdit")
        self.eventQualifier2LineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.eventQualifier2LineEdit, 3, 10, 1, 3)

        self.origCreationDateLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.origCreationDateLineEdit.setObjectName(u"origCreationDateLineEdit")
        self.origCreationDateLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.origCreationDateLineEdit, 5, 12, 1, 1)

        self.startDateTimeLabel = QLabel(self.eventHeaderGroupBox)
        self.startDateTimeLabel.setObjectName(u"startDateTimeLabel")

        self.gridLayout_3.addWidget(self.startDateTimeLabel, 6, 0, 1, 8)

        self.endLongitudeLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.endLongitudeLineEdit.setObjectName(u"endLongitudeLineEdit")
        self.endLongitudeLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.endLongitudeLineEdit, 11, 8, 1, 5)

        self.minDepthLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.minDepthLineEdit.setObjectName(u"minDepthLineEdit")
        self.minDepthLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.minDepthLineEdit, 12, 3, 1, 10)

        self.startDateTimeLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.startDateTimeLineEdit.setObjectName(u"startDateTimeLineEdit")
        self.startDateTimeLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.startDateTimeLineEdit, 6, 9, 1, 4)

        self.maxDepthLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.maxDepthLineEdit.setObjectName(u"maxDepthLineEdit")
        self.maxDepthLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.maxDepthLineEdit, 13, 3, 1, 10)

        self.depthOffBottomLabel = QLabel(self.eventHeaderGroupBox)
        self.depthOffBottomLabel.setObjectName(u"depthOffBottomLabel")

        self.gridLayout_3.addWidget(self.depthOffBottomLabel, 16, 0, 1, 11)

        self.soundingLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.soundingLineEdit.setObjectName(u"soundingLineEdit")
        self.soundingLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.soundingLineEdit, 15, 2, 1, 11)

        self.eventNumberLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.eventNumberLineEdit.setObjectName(u"eventNumberLineEdit")
        self.eventNumberLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.eventNumberLineEdit, 1, 8, 1, 5)

        self.creationDateLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.creationDateLineEdit.setObjectName(u"creationDateLineEdit")
        self.creationDateLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.creationDateLineEdit, 4, 8, 1, 5)

        self.endDateTimeLabel = QLabel(self.eventHeaderGroupBox)
        self.endDateTimeLabel.setObjectName(u"endDateTimeLabel")

        self.gridLayout_3.addWidget(self.endDateTimeLabel, 7, 0, 1, 6)

        self.stationNameLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.stationNameLineEdit.setObjectName(u"stationNameLineEdit")
        self.stationNameLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.stationNameLineEdit, 17, 6, 1, 7)

        self.creationDateLabel = QLabel(self.eventHeaderGroupBox)
        self.creationDateLabel.setObjectName(u"creationDateLabel")

        self.gridLayout_3.addWidget(self.creationDateLabel, 4, 0, 1, 6)

        self.dataTypeLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.dataTypeLineEdit.setObjectName(u"dataTypeLineEdit")
        self.dataTypeLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.dataTypeLineEdit, 0, 1, 1, 12)

        self.initialLongitudeLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.initialLongitudeLineEdit.setObjectName(u"initialLongitudeLineEdit")
        self.initialLongitudeLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.initialLongitudeLineEdit, 9, 11, 1, 2)

        self.samplingIntervalLabel = QLabel(self.eventHeaderGroupBox)
        self.samplingIntervalLabel.setObjectName(u"samplingIntervalLabel")

        self.gridLayout_3.addWidget(self.samplingIntervalLabel, 14, 0, 1, 12)

        self.depthOffBottomLineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.depthOffBottomLineEdit.setObjectName(u"depthOffBottomLineEdit")
        self.depthOffBottomLineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.depthOffBottomLineEdit, 16, 12, 1, 1)

        self.eventQualifier1LineEdit = QLineEdit(self.eventHeaderGroupBox)
        self.eventQualifier1LineEdit.setObjectName(u"eventQualifier1LineEdit")
        self.eventQualifier1LineEdit.setFont(font)

        self.gridLayout_3.addWidget(self.eventQualifier1LineEdit, 2, 10, 1, 3)

        self.yearLabel = QLabel(ODF_Metadata_Form)
        self.yearLabel.setObjectName(u"yearLabel")
        self.yearLabel.setGeometry(QRect(30, 50, 341, 39))
        self.yearLabel.setFont(font2)
        self.yearLineEdit = QLineEdit(ODF_Metadata_Form)
        self.yearLineEdit.setObjectName(u"yearLineEdit")
        self.yearLineEdit.setGeometry(QRect(370, 60, 121, 22))
        font3 = QFont()
        font3.setPointSize(9)
        font3.setBold(False)
        self.yearLineEdit.setFont(font3)
        self.yearLineEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.retranslateUi(ODF_Metadata_Form)

        QMetaObject.connectSlotsByName(ODF_Metadata_Form)
    # setupUi

    def retranslateUi(self, ODF_Metadata_Form):
        ODF_Metadata_Form.setWindowTitle(QCoreApplication.translate("ODF_Metadata_Form", u"Form", None))
        self.okPushButton.setText(QCoreApplication.translate("ODF_Metadata_Form", u"OK", None))
        self.missionTemplateSelectorLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"MISSION TEMPLATE SELECTOR", None))
        self.cruiseHeaderGoupBox.setTitle(QCoreApplication.translate("ODF_Metadata_Form", u"CRUISE_HEADER", None))
        self.cruiseDesciptionLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"CRUISE_DESCRIPTION:", None))
        self.countryInstituteCodeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"COUNTRY_INSTITUTE_CODE:", None))
        self.chiefScientistLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"CHIEF_SCIENTIST:", None))
        self.organizationLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"ORGANIZATION:", None))
        self.platformLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"PLATFORM:", None))
        self.cruiseNumberLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"CRUISE_NUMBER:", None))
        self.startDateLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"START_DATE:", None))
        self.cruiseNameLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"CRUISE_NAME:", None))
        self.endDateLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"END_DATE:", None))
        self.cancelPushButton.setText(QCoreApplication.translate("ODF_Metadata_Form", u"CANCEL", None))
        self.eventHeaderGroupBox.setTitle(QCoreApplication.translate("ODF_Metadata_Form", u"EVENT_HEADER", None))
        self.minDepthLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"MIN_DEPTH:", None))
        self.stationNameLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"STATION_NAME:", None))
        self.eventNumberLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"EVENT_NUMBER:", None))
        self.eventQualifier2Label.setText(QCoreApplication.translate("ODF_Metadata_Form", u"EVENT_QUALIFIER2:", None))
        self.endLatitudeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"END_LATITUDE:", None))
        self.soundingLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"SOUNDING:", None))
        self.origCreationDateLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"ORIG_CREATION_DATE:", None))
        self.dataTypeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"DATA_TYPE:", None))
        self.initialLongitudeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"INITIAL_LONGITUDE:", None))
        self.eventCommentsLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"EVENT_COMMENTS:", None))
        self.initialLatitudeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"INITIAL_LATITUDE:", None))
        self.setNumberLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"SET_NUMBER:", None))
        self.eventQualifier1Label.setText(QCoreApplication.translate("ODF_Metadata_Form", u"EVENT_QUALIFIER1:", None))
        self.maxDepthLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"MAX_DEPTH:", None))
        self.endLongitudeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"END_LONGITUDE:", None))
        self.startDateTimeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"START_DATE_TIME:", None))
        self.depthOffBottomLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"DEPTH_OFF_BOTTOM:", None))
        self.endDateTimeLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"END_DATE_TIME:", None))
        self.creationDateLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"CREATION_DATE:", None))
        self.samplingIntervalLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"SAMPLING_INTERVAL:", None))
        self.yearLabel.setText(QCoreApplication.translate("ODF_Metadata_Form", u"PLEASE ENTER YEAR DATA WAS COLLECTED:", None))
    # retranslateUi

