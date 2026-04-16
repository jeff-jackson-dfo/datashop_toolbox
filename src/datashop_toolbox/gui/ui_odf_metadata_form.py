################################################################################
## Form generated from reading UI file 'odf_metadata_form.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QMetaObject,
    QRect,
    Qt,
)
from PySide6.QtGui import (
    QFont,
)
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class Ui_odf_metadata_form:
    def setupUi(self, odf_metadata_form):
        if not odf_metadata_form.objectName():
            odf_metadata_form.setObjectName("odf_metadata_form")
        odf_metadata_form.setWindowModality(Qt.WindowModality.NonModal)
        odf_metadata_form.resize(1100, 822)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(odf_metadata_form.sizePolicy().hasHeightForWidth())
        odf_metadata_form.setSizePolicy(sizePolicy)
        self.mission_template_selector_combo_box = QComboBox(odf_metadata_form)
        self.mission_template_selector_combo_box.setObjectName("mission_template_selector_combo_box")
        self.mission_template_selector_combo_box.setGeometry(QRect(270, 20, 311, 22))
        font = QFont()
        font.setPointSize(9)
        self.mission_template_selector_combo_box.setFont(font)
        self.ok_push_button = QPushButton(odf_metadata_form)
        self.ok_push_button.setObjectName("ok_push_button")
        self.ok_push_button.setGeometry(QRect(310, 730, 201, 61))
        font1 = QFont()
        font1.setPointSize(16)
        font1.setBold(True)
        font1.setKerning(True)
        self.ok_push_button.setFont(font1)
        self.ok_push_button.setAutoFillBackground(False)
        self.mission_template_selector_label = QLabel(odf_metadata_form)
        self.mission_template_selector_label.setObjectName("mission_template_selector_label")
        self.mission_template_selector_label.setGeometry(QRect(30, 10, 231, 39))
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.mission_template_selector_label.setFont(font2)
        self.cruise_header_group_box = QGroupBox(odf_metadata_form)
        self.cruise_header_group_box.setObjectName("cruise_header_group_box")
        self.cruise_header_group_box.setGeometry(QRect(20, 110, 491, 282))
        self.gridLayout_2 = QGridLayout(self.cruise_header_group_box)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.cruise_number_line_edit = QLineEdit(self.cruise_header_group_box)
        self.cruise_number_line_edit.setObjectName("cruise_number_line_edit")
        self.cruise_number_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.cruise_number_line_edit, 1, 4, 1, 3)

        self.country_institute_code_line_edit = QLineEdit(self.cruise_header_group_box)
        self.country_institute_code_line_edit.setObjectName("country_institute_code_line_edit")
        self.country_institute_code_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.country_institute_code_line_edit, 0, 6, 1, 1)

        self.platform_line_edit = QLineEdit(self.cruise_header_group_box)
        self.platform_line_edit.setObjectName("platform_line_edit")
        self.platform_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.platform_line_edit, 6, 2, 1, 5)

        self.cruise_description_label = QLabel(self.cruise_header_group_box)
        self.cruise_description_label.setObjectName("cruise_description_label")

        self.gridLayout_2.addWidget(self.cruise_description_label, 8, 0, 1, 5)

        self.end_date_line_edit = QLineEdit(self.cruise_header_group_box)
        self.end_date_line_edit.setObjectName("end_date_line_edit")
        self.end_date_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.end_date_line_edit, 5, 1, 1, 6)

        self.country_institute_code_label = QLabel(self.cruise_header_group_box)
        self.country_institute_code_label.setObjectName("country_institute_code_label")

        self.gridLayout_2.addWidget(self.country_institute_code_label, 0, 0, 1, 6)

        self.chief_scientist_label = QLabel(self.cruise_header_group_box)
        self.chief_scientist_label.setObjectName("chief_scientist_label")

        self.gridLayout_2.addWidget(self.chief_scientist_label, 3, 0, 1, 4)

        self.organization_label = QLabel(self.cruise_header_group_box)
        self.organization_label.setObjectName("organization_label")

        self.gridLayout_2.addWidget(self.organization_label, 2, 0, 1, 4)

        self.platform_label = QLabel(self.cruise_header_group_box)
        self.platform_label.setObjectName("platform_label")

        self.gridLayout_2.addWidget(self.platform_label, 6, 0, 1, 1)

        self.organization_line_edit = QLineEdit(self.cruise_header_group_box)
        self.organization_line_edit.setObjectName("organization_line_edit")
        self.organization_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.organization_line_edit, 2, 4, 1, 3)

        self.cruise_number_label = QLabel(self.cruise_header_group_box)
        self.cruise_number_label.setObjectName("cruise_number_label")

        self.gridLayout_2.addWidget(self.cruise_number_label, 1, 0, 1, 4)

        self.start_date_label = QLabel(self.cruise_header_group_box)
        self.start_date_label.setObjectName("start_date_label")

        self.gridLayout_2.addWidget(self.start_date_label, 4, 0, 1, 2)

        self.start_date_line_edit = QLineEdit(self.cruise_header_group_box)
        self.start_date_line_edit.setObjectName("start_date_line_edit")
        self.start_date_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.start_date_line_edit, 4, 2, 1, 5)

        self.cruise_description_line_edit = QLineEdit(self.cruise_header_group_box)
        self.cruise_description_line_edit.setObjectName("cruise_description_line_edit")
        self.cruise_description_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.cruise_description_line_edit, 8, 5, 1, 2)

        self.cruise_name_label = QLabel(self.cruise_header_group_box)
        self.cruise_name_label.setObjectName("cruise_name_label")

        self.gridLayout_2.addWidget(self.cruise_name_label, 7, 0, 1, 3)

        self.chief_scientist_line_edit = QLineEdit(self.cruise_header_group_box)
        self.chief_scientist_line_edit.setObjectName("chief_scientist_line_edit")
        self.chief_scientist_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.chief_scientist_line_edit, 3, 4, 1, 3)

        self.end_date_label = QLabel(self.cruise_header_group_box)
        self.end_date_label.setObjectName("end_date_label")

        self.gridLayout_2.addWidget(self.end_date_label, 5, 0, 1, 1)

        self.cruise_name_line_edit = QLineEdit(self.cruise_header_group_box)
        self.cruise_name_line_edit.setObjectName("cruise_name_line_edit")
        self.cruise_name_line_edit.setFont(font)

        self.gridLayout_2.addWidget(self.cruise_name_line_edit, 7, 3, 1, 4)

        self.cancel_push_button = QPushButton(odf_metadata_form)
        self.cancel_push_button.setObjectName("cancel_push_button")
        self.cancel_push_button.setGeometry(QRect(520, 730, 201, 61))
        self.cancel_push_button.setFont(font1)
        self.cancel_push_button.setAutoFillBackground(False)
        self.event_header_group_box = QGroupBox(odf_metadata_form)
        self.event_header_group_box.setObjectName("event_header_group_box")
        self.event_header_group_box.setGeometry(QRect(520, 110, 521, 590))
        self.gridLayout_3 = QGridLayout(self.event_header_group_box)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.min_depth_label = QLabel(self.event_header_group_box)
        self.min_depth_label.setObjectName("min_depth_label")

        self.gridLayout_3.addWidget(self.min_depth_label, 12, 0, 1, 1)

        self.station_name_label = QLabel(self.event_header_group_box)
        self.station_name_label.setObjectName("station_name_label")

        self.gridLayout_3.addWidget(self.station_name_label, 17, 0, 1, 5)

        self.event_number_label = QLabel(self.event_header_group_box)
        self.event_number_label.setObjectName("event_number_label")

        self.gridLayout_3.addWidget(self.event_number_label, 1, 0, 1, 6)

        self.event_qualifier2_label = QLabel(self.event_header_group_box)
        self.event_qualifier2_label.setObjectName("event_qualifier2_label")

        self.gridLayout_3.addWidget(self.event_qualifier2_label, 3, 0, 1, 9)

        self.end_latitude_label = QLabel(self.event_header_group_box)
        self.end_latitude_label.setObjectName("end_latitude_label")

        self.gridLayout_3.addWidget(self.end_latitude_label, 10, 0, 1, 4)

        self.sounding_label = QLabel(self.event_header_group_box)
        self.sounding_label.setObjectName("sounding_label")

        self.gridLayout_3.addWidget(self.sounding_label, 15, 0, 1, 1)

        self.orig_creation_date_label = QLabel(self.event_header_group_box)
        self.orig_creation_date_label.setObjectName("orig_creation_date_label")

        self.gridLayout_3.addWidget(self.orig_creation_date_label, 5, 0, 1, 12)

        self.data_type_label = QLabel(self.event_header_group_box)
        self.data_type_label.setObjectName("data_type_label")

        self.gridLayout_3.addWidget(self.data_type_label, 0, 0, 1, 1)

        self.initial_longitude_label = QLabel(self.event_header_group_box)
        self.initial_longitude_label.setObjectName("initial_longitude_label")

        self.gridLayout_3.addWidget(self.initial_longitude_label, 9, 0, 1, 10)

        self.end_date_time_line_edit = QLineEdit(self.event_header_group_box)
        self.end_date_time_line_edit.setObjectName("end_date_time_line_edit")
        self.end_date_time_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.end_date_time_line_edit, 7, 7, 1, 6)

        self.event_comments_label = QLabel(self.event_header_group_box)
        self.event_comments_label.setObjectName("event_comments_label")

        self.gridLayout_3.addWidget(self.event_comments_label, 19, 0, 1, 10)

        self.initial_latitude_label = QLabel(self.event_header_group_box)
        self.initial_latitude_label.setObjectName("initial_latitude_label")

        self.gridLayout_3.addWidget(self.initial_latitude_label, 8, 0, 1, 7)

        self.initial_latitude_line_edit = QLineEdit(self.event_header_group_box)
        self.initial_latitude_line_edit.setObjectName("initial_latitude_line_edit")
        self.initial_latitude_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.initial_latitude_line_edit, 8, 8, 1, 5)

        self.set_number_label = QLabel(self.event_header_group_box)
        self.set_number_label.setObjectName("set_number_label")

        self.gridLayout_3.addWidget(self.set_number_label, 18, 0, 1, 3)

        self.event_comments_line_edit = QLineEdit(self.event_header_group_box)
        self.event_comments_line_edit.setObjectName("event_comments_line_edit")
        self.event_comments_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.event_comments_line_edit, 19, 10, 1, 3)

        self.event_qualifier1_label = QLabel(self.event_header_group_box)
        self.event_qualifier1_label.setObjectName("event_qualifier1_label")

        self.gridLayout_3.addWidget(self.event_qualifier1_label, 2, 0, 1, 9)

        self.max_depth_label = QLabel(self.event_header_group_box)
        self.max_depth_label.setObjectName("max_depth_label")

        self.gridLayout_3.addWidget(self.max_depth_label, 13, 0, 1, 2)

        self.sampling_interval_line_edit = QLineEdit(self.event_header_group_box)
        self.sampling_interval_line_edit.setObjectName("sampling_interval_line_edit")
        self.sampling_interval_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.sampling_interval_line_edit, 14, 12, 1, 1)

        self.end_longitude_label = QLabel(self.event_header_group_box)
        self.end_longitude_label.setObjectName("end_longitude_label")

        self.gridLayout_3.addWidget(self.end_longitude_label, 11, 0, 1, 6)

        self.set_number_line_edit = QLineEdit(self.event_header_group_box)
        self.set_number_line_edit.setObjectName("set_number_line_edit")
        self.set_number_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.set_number_line_edit, 18, 4, 1, 9)

        self.end_latitude_line_edit = QLineEdit(self.event_header_group_box)
        self.end_latitude_line_edit.setObjectName("end_latitude_line_edit")
        self.end_latitude_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.end_latitude_line_edit, 10, 5, 1, 8)

        self.event_qualifier2_line_edit = QLineEdit(self.event_header_group_box)
        self.event_qualifier2_line_edit.setObjectName("event_qualifier2_line_edit")
        self.event_qualifier2_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.event_qualifier2_line_edit, 3, 10, 1, 3)

        self.orig_creation_date_line_edit = QLineEdit(self.event_header_group_box)
        self.orig_creation_date_line_edit.setObjectName("orig_creation_date_line_edit")
        self.orig_creation_date_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.orig_creation_date_line_edit, 5, 12, 1, 1)

        self.start_date_time_label = QLabel(self.event_header_group_box)
        self.start_date_time_label.setObjectName("start_date_time_label")

        self.gridLayout_3.addWidget(self.start_date_time_label, 6, 0, 1, 8)

        self.end_longitude_line_edit = QLineEdit(self.event_header_group_box)
        self.end_longitude_line_edit.setObjectName("end_longitude_line_edit")
        self.end_longitude_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.end_longitude_line_edit, 11, 8, 1, 5)

        self.min_depth_line_edit = QLineEdit(self.event_header_group_box)
        self.min_depth_line_edit.setObjectName("min_depth_line_edit")
        self.min_depth_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.min_depth_line_edit, 12, 3, 1, 10)

        self.start_date_time_line_edit = QLineEdit(self.event_header_group_box)
        self.start_date_time_line_edit.setObjectName("start_date_time_line_edit")
        self.start_date_time_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.start_date_time_line_edit, 6, 9, 1, 4)

        self.max_depth_line_edit = QLineEdit(self.event_header_group_box)
        self.max_depth_line_edit.setObjectName("max_depth_line_edit")
        self.max_depth_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.max_depth_line_edit, 13, 3, 1, 10)

        self.depth_off_bottom_label = QLabel(self.event_header_group_box)
        self.depth_off_bottom_label.setObjectName("depth_off_bottom_label")

        self.gridLayout_3.addWidget(self.depth_off_bottom_label, 16, 0, 1, 11)

        self.sounding_line_edit = QLineEdit(self.event_header_group_box)
        self.sounding_line_edit.setObjectName("sounding_line_edit")
        self.sounding_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.sounding_line_edit, 15, 2, 1, 11)

        self.event_number_line_edit = QLineEdit(self.event_header_group_box)
        self.event_number_line_edit.setObjectName("event_number_line_edit")
        self.event_number_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.event_number_line_edit, 1, 8, 1, 5)

        self.creation_date_line_edit = QLineEdit(self.event_header_group_box)
        self.creation_date_line_edit.setObjectName("creation_date_line_edit")
        self.creation_date_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.creation_date_line_edit, 4, 8, 1, 5)

        self.end_date_time_label = QLabel(self.event_header_group_box)
        self.end_date_time_label.setObjectName("end_date_time_label")

        self.gridLayout_3.addWidget(self.end_date_time_label, 7, 0, 1, 6)

        self.station_name_line_edit = QLineEdit(self.event_header_group_box)
        self.station_name_line_edit.setObjectName("station_name_line_edit")
        self.station_name_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.station_name_line_edit, 17, 6, 1, 7)

        self.creation_date_label = QLabel(self.event_header_group_box)
        self.creation_date_label.setObjectName("creation_date_label")

        self.gridLayout_3.addWidget(self.creation_date_label, 4, 0, 1, 6)

        self.data_type_line_edit = QLineEdit(self.event_header_group_box)
        self.data_type_line_edit.setObjectName("data_type_line_edit")
        self.data_type_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.data_type_line_edit, 0, 1, 1, 12)

        self.initial_longitude_line_edit = QLineEdit(self.event_header_group_box)
        self.initial_longitude_line_edit.setObjectName("initial_longitude_line_edit")
        self.initial_longitude_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.initial_longitude_line_edit, 9, 11, 1, 2)

        self.sampling_interval_label = QLabel(self.event_header_group_box)
        self.sampling_interval_label.setObjectName("sampling_interval_label")

        self.gridLayout_3.addWidget(self.sampling_interval_label, 14, 0, 1, 12)

        self.depth_off_bottom_line_edit = QLineEdit(self.event_header_group_box)
        self.depth_off_bottom_line_edit.setObjectName("depth_off_bottom_line_edit")
        self.depth_off_bottom_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.depth_off_bottom_line_edit, 16, 12, 1, 1)

        self.event_qualifier1_line_edit = QLineEdit(self.event_header_group_box)
        self.event_qualifier1_line_edit.setObjectName("event_qualifier1_line_edit")
        self.event_qualifier1_line_edit.setFont(font)

        self.gridLayout_3.addWidget(self.event_qualifier1_line_edit, 2, 10, 1, 3)

        self.year_label = QLabel(odf_metadata_form)
        self.year_label.setObjectName("year_label")
        self.year_label.setGeometry(QRect(30, 50, 341, 39))
        self.year_label.setFont(font2)
        self.year_line_edit = QLineEdit(odf_metadata_form)
        self.year_line_edit.setObjectName("year_line_edit")
        self.year_line_edit.setGeometry(QRect(370, 60, 121, 22))
        font3 = QFont()
        font3.setPointSize(9)
        font3.setBold(False)
        self.year_line_edit.setFont(font3)
        self.year_line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        QWidget.setTabOrder(self.mission_template_selector_combo_box, self.year_line_edit)
        QWidget.setTabOrder(self.year_line_edit, self.country_institute_code_line_edit)
        QWidget.setTabOrder(self.country_institute_code_line_edit, self.cruise_number_line_edit)
        QWidget.setTabOrder(self.cruise_number_line_edit, self.organization_line_edit)
        QWidget.setTabOrder(self.organization_line_edit, self.chief_scientist_line_edit)
        QWidget.setTabOrder(self.chief_scientist_line_edit, self.start_date_line_edit)
        QWidget.setTabOrder(self.start_date_line_edit, self.end_date_line_edit)
        QWidget.setTabOrder(self.end_date_line_edit, self.platform_line_edit)
        QWidget.setTabOrder(self.platform_line_edit, self.cruise_name_line_edit)
        QWidget.setTabOrder(self.cruise_name_line_edit, self.cruise_description_line_edit)
        QWidget.setTabOrder(self.cruise_description_line_edit, self.data_type_line_edit)
        QWidget.setTabOrder(self.data_type_line_edit, self.event_number_line_edit)
        QWidget.setTabOrder(self.event_number_line_edit, self.event_qualifier1_line_edit)
        QWidget.setTabOrder(self.event_qualifier1_line_edit, self.event_qualifier2_line_edit)
        QWidget.setTabOrder(self.event_qualifier2_line_edit, self.creation_date_line_edit)
        QWidget.setTabOrder(self.creation_date_line_edit, self.orig_creation_date_line_edit)
        QWidget.setTabOrder(self.orig_creation_date_line_edit, self.start_date_time_line_edit)
        QWidget.setTabOrder(self.start_date_time_line_edit, self.end_date_time_line_edit)
        QWidget.setTabOrder(self.end_date_time_line_edit, self.initial_latitude_line_edit)
        QWidget.setTabOrder(self.initial_latitude_line_edit, self.initial_longitude_line_edit)
        QWidget.setTabOrder(self.initial_longitude_line_edit, self.end_latitude_line_edit)
        QWidget.setTabOrder(self.end_latitude_line_edit, self.end_longitude_line_edit)
        QWidget.setTabOrder(self.end_longitude_line_edit, self.min_depth_line_edit)
        QWidget.setTabOrder(self.min_depth_line_edit, self.max_depth_line_edit)
        QWidget.setTabOrder(self.max_depth_line_edit, self.sampling_interval_line_edit)
        QWidget.setTabOrder(self.sampling_interval_line_edit, self.sounding_line_edit)
        QWidget.setTabOrder(self.sounding_line_edit, self.depth_off_bottom_line_edit)
        QWidget.setTabOrder(self.depth_off_bottom_line_edit, self.station_name_line_edit)
        QWidget.setTabOrder(self.station_name_line_edit, self.set_number_line_edit)
        QWidget.setTabOrder(self.set_number_line_edit, self.event_comments_line_edit)
        QWidget.setTabOrder(self.event_comments_line_edit, self.ok_push_button)
        QWidget.setTabOrder(self.ok_push_button, self.cancel_push_button)

        self.retranslateUi(odf_metadata_form)

        QMetaObject.connectSlotsByName(odf_metadata_form)
    # setupUi

    def retranslateUi(self, odf_metadata_form):
        odf_metadata_form.setWindowTitle(QCoreApplication.translate("odf_metadata_form", "Form", None))
        self.ok_push_button.setText(QCoreApplication.translate("odf_metadata_form", "OK", None))
        self.mission_template_selector_label.setText(QCoreApplication.translate("odf_metadata_form", "MISSION TEMPLATE SELECTOR", None))  # noqa: E501
        self.cruise_header_group_box.setTitle(QCoreApplication.translate("odf_metadata_form", "CRUISE_HEADER", None))
        self.cruise_description_label.setText(QCoreApplication.translate("odf_metadata_form", "CRUISE_DESCRIPTION:", None))  # noqa: E501
        self.country_institute_code_label.setText(QCoreApplication.translate("odf_metadata_form", "COUNTRY_INSTITUTE_CODE:", None))  # noqa: E501
        self.chief_scientist_label.setText(QCoreApplication.translate("odf_metadata_form", "CHIEF_SCIENTIST:", None))
        self.organization_label.setText(QCoreApplication.translate("odf_metadata_form", "ORGANIZATION:", None))
        self.platform_label.setText(QCoreApplication.translate("odf_metadata_form", "PLATFORM:", None))
        self.cruise_number_label.setText(QCoreApplication.translate("odf_metadata_form", "CRUISE_NUMBER:", None))
        self.start_date_label.setText(QCoreApplication.translate("odf_metadata_form", "START_DATE:", None))
        self.cruise_name_label.setText(QCoreApplication.translate("odf_metadata_form", "CRUISE_NAME:", None))
        self.end_date_label.setText(QCoreApplication.translate("odf_metadata_form", "END_DATE:", None))
        self.cancel_push_button.setText(QCoreApplication.translate("odf_metadata_form", "CANCEL", None))
        self.event_header_group_box.setTitle(QCoreApplication.translate("odf_metadata_form", "EVENT_HEADER", None))
        self.min_depth_label.setText(QCoreApplication.translate("odf_metadata_form", "MIN_DEPTH:", None))
        self.station_name_label.setText(QCoreApplication.translate("odf_metadata_form", "STATION_NAME:", None))
        self.event_number_label.setText(QCoreApplication.translate("odf_metadata_form", "EVENT_NUMBER:", None))
        self.event_qualifier2_label.setText(QCoreApplication.translate("odf_metadata_form", "EVENT_QUALIFIER2:", None))
        self.end_latitude_label.setText(QCoreApplication.translate("odf_metadata_form", "END_LATITUDE:", None))
        self.sounding_label.setText(QCoreApplication.translate("odf_metadata_form", "SOUNDING:", None))
        self.orig_creation_date_label.setText(QCoreApplication.translate("odf_metadata_form", "ORIG_CREATION_DATE:", None))  # noqa: E501
        self.data_type_label.setText(QCoreApplication.translate("odf_metadata_form", "DATA_TYPE:", None))
        self.initial_longitude_label.setText(QCoreApplication.translate("odf_metadata_form", "INITIAL_LONGITUDE:", None))  # noqa: E501
        self.event_comments_label.setText(QCoreApplication.translate("odf_metadata_form", "EVENT_COMMENTS:", None))
        self.initial_latitude_label.setText(QCoreApplication.translate("odf_metadata_form", "INITIAL_LATITUDE:", None))
        self.set_number_label.setText(QCoreApplication.translate("odf_metadata_form", "SET_NUMBER:", None))
        self.event_qualifier1_label.setText(QCoreApplication.translate("odf_metadata_form", "EVENT_QUALIFIER1:", None))
        self.max_depth_label.setText(QCoreApplication.translate("odf_metadata_form", "MAX_DEPTH:", None))
        self.end_longitude_label.setText(QCoreApplication.translate("odf_metadata_form", "END_LONGITUDE:", None))
        self.start_date_time_label.setText(QCoreApplication.translate("odf_metadata_form", "START_DATE_TIME:", None))
        self.depth_off_bottom_label.setText(QCoreApplication.translate("odf_metadata_form", "DEPTH_OFF_BOTTOM:", None))
        self.end_date_time_label.setText(QCoreApplication.translate("odf_metadata_form", "END_DATE_TIME:", None))
        self.creation_date_label.setText(QCoreApplication.translate("odf_metadata_form", "CREATION_DATE:", None))
        self.sampling_interval_label.setText(QCoreApplication.translate("odf_metadata_form", "SAMPLING_INTERVAL:", None))  # noqa: E501
        self.year_label.setText(QCoreApplication.translate("odf_metadata_form", "PLEASE ENTER YEAR DATA WAS COLLECTED:", None))  # noqa: E501
    # retranslateUi

