# odf_header_form.py
# -*- coding: utf-8 -*-

from datetime import datetime
from icecream import ic
from pathlib import Path
import json
import sys

from PySide6.QtCore import Qt, QLocale, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QMainWindow, QDialogButtonBox, QMessageBox, QApplication
)
from PySide6.QtGui import QDoubleValidator, QIntValidator

# You need to run the following command to generate the ui_odf_metadata_form.py file:
#     pyside6-uic odf_metadata_form.ui -o ui_odf_metadata_form.py
from ui_odf_metadata_form import Ui_ODF_Metadata_Form

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.validated_base import check_datetime


class OdfMetadataForm(QWidget):
    """
    Reusable content widget that hosts the controls from Ui_ODF_Metadata_Window.
    Because the .ui was compiled as a QMainWindow, we use a temporary host
    QMainWindow to build it, then reparent the centralwidget into this QWidget.
    """

    # Signals you can use from wrappers
    submitted = Signal(object)   # emits OdfHeader on OK
    cancelled = Signal()         # emits on Cancel

    def __init__(self, parent=None, mission_templates_path: Path | None = None):
        super().__init__(parent)

        # ---- 1) Build UI using a temporary QMainWindow host (adapter pattern) ----
        self.ui = Ui_ODF_Metadata_Form()

        self.ui.setupUi(self)

        # ---- 2) Init state and helpers ----
        base_dir = Path(__file__).resolve().parent
        # Default to a file next to this module called mission_header_templates.json
        self._mission_templates_path = mission_templates_path or (base_dir / "mission_header_templates.json")
        self._mission_templates: dict[str, dict] = {}
        
        # ---- 3) Wire up behaviour ----
        self._setup_validators()
        self._populate_mission_templates()
        self._connect_signals()

    # -----------------------------
    # Setup helpers
    # -----------------------------
    def _setup_validators(self):
        # Placeholders
        self.ui.yearLineEdit.setPlaceholderText("####")
        self.ui.initialLatitudeLineEdit.setPlaceholderText("####.######")
        self.ui.initialLongitudeLineEdit.setPlaceholderText("####.######")
        self.ui.endLatitudeLineEdit.setPlaceholderText("####.######")
        self.ui.endLongitudeLineEdit.setPlaceholderText("####.######")
        self.ui.minDepthLineEdit.setPlaceholderText("####.##")
        self.ui.maxDepthLineEdit.setPlaceholderText("####.##")
        self.ui.samplingIntervalLineEdit.setPlaceholderText("####.####")
        self.ui.soundingLineEdit.setPlaceholderText("####.##")
        self.ui.depthOffBottomLineEdit.setPlaceholderText("####.##")

        year_validator = QIntValidator(1900, 2050)
        latitude_validator = QDoubleValidator(-90.0, 90.0, 6)
        longitude_validator = QDoubleValidator(-180.0, 180.0, 6)
        depth_validator = QDoubleValidator(0.0, 6000.0, 2)
        sample_interval_validator = QDoubleValidator(0.0, 1000.0, 4)

        locale = QLocale(QLocale.English, QLocale.UnitedStates)
        for v in (latitude_validator, longitude_validator, depth_validator, sample_interval_validator):
            v.setLocale(locale)
            v.setNotation(QDoubleValidator.StandardNotation)
        
        # Apply to fields (note: endLatitude uses latitude validator)
        self.ui.yearLineEdit.setValidator(year_validator)
        self.ui.initialLatitudeLineEdit.setValidator(latitude_validator)
        self.ui.initialLongitudeLineEdit.setValidator(longitude_validator)
        self.ui.endLatitudeLineEdit.setValidator(latitude_validator)
        self.ui.endLongitudeLineEdit.setValidator(longitude_validator)
        self.ui.minDepthLineEdit.setValidator(depth_validator)
        self.ui.maxDepthLineEdit.setValidator(depth_validator)
        self.ui.samplingIntervalLineEdit.setValidator(sample_interval_validator)
        self.ui.soundingLineEdit.setValidator(depth_validator)
        self.ui.depthOffBottomLineEdit.setValidator(depth_validator)

    def _populate_mission_templates(self):
        """Load top-level keys from mission_header_templates.json into the combo."""
        self._mission_templates = {}
        if self._mission_templates_path.exists():
            try:
                self._mission_templates = json.loads(self._mission_templates_path.read_text(encoding="utf-8"))
            except Exception as e:
                QMessageBox.warning(self, "Templates", f"Failed to read templates:\n{e}")
        else:
            # Fill UI to indicate none, but keep working
            self.ui.missionTemplateSelectorComboBox.clear()
            self.ui.missionTemplateSelectorComboBox.addItem("No templates found")
            return

        keys = list(self._mission_templates.keys())
        # Hide the shared section (if present) from the selector
        if "event_header" in keys:
            keys.remove("event_header")
        # Insert '---' on top as a "no selection"
        keys.insert(0, "---")

        self.ui.missionTemplateSelectorComboBox.clear()
        self.ui.missionTemplateSelectorComboBox.addItems(keys)

    def _populate_year(self):
        # Populate year with current year
        self.ui.yearLineEdit.setText(str(datetime.now().year))

    def _show_warning_dialog(self):
        # Defer to ensure parent (dialog) is actually visible
        def _run():
            parent = self.window() if isinstance(self.window(), QWidget) else self
            QMessageBox.warning(
                parent,
                "Warning!!",
                (
                    "The Year line edit box was automatically populated with the current year. "
                    "If this is not the year the data was acquired then please change it."
                ),
            )

        QTimer.singleShot(0, _run)

    def showEvent(self, event):
        """Overrides the show event to run code after the dialog is visible."""
        super().showEvent(event)  # Call base class handler
        # Populate year now
        self._on_dialog_visible()
        # Show warning AFTER the parent dialog is exposed
        self._show_warning_dialog()

    def _on_dialog_visible(self):
        """Function that runs when the dialog appears."""
        # Perform tasks like loading data, starting animations, etc.
        self._populate_year()

    def _connect_signals(self):
        self.ui.missionTemplateSelectorComboBox.currentTextChanged.connect(self._on_template_changed)
        # Your UI provides dedicated OK/Cancel buttons on the form
        self.ui.okPushButton.clicked.connect(self._on_ok_clicked)
        self.ui.cancelPushButton.clicked.connect(self._on_cancel_clicked)

    # -----------------------------
    # Template loading
    # -----------------------------
    def _clear_cruise_header_fields(self):
        for w in (
            self.ui.countryInstituteCodeLineEdit,
            self.ui.cruiseNumberLineEdit,
            self.ui.organizationLineEdit,
            self.ui.chiefScientistLineEdit,
            self.ui.startDateLineEdit,
            self.ui.endDateLineEdit,
            self.ui.platformLineEdit,
            self.ui.cruiseNameLineEdit,
            self.ui.cruiseDescriptionLineEdit,  # correct attribute name in UI  # noqa
        ):
            w.clear()

    def _clear_event_header_fields(self):
        for w in (
            self.ui.dataTypeLineEdit,
            self.ui.eventNumberLineEdit,
            self.ui.eventQualifier1LineEdit,
            self.ui.eventQualifier2LineEdit,
            self.ui.creationDateLineEdit,
            self.ui.origCreationDateLineEdit,
            self.ui.startDateTimeLineEdit,
            self.ui.endDateTimeLineEdit,
            self.ui.initialLatitudeLineEdit,
            self.ui.initialLongitudeLineEdit,
            self.ui.endLatitudeLineEdit,
            self.ui.endLongitudeLineEdit,
            self.ui.minDepthLineEdit,
            self.ui.maxDepthLineEdit,
            self.ui.samplingIntervalLineEdit,
            self.ui.soundingLineEdit,
            self.ui.depthOffBottomLineEdit,
            self.ui.stationNameLineEdit,
            self.ui.setNumberLineEdit,
            self.ui.eventCommentsLineEdit,
        ):
            w.clear()

    @Slot(str)
    def _on_template_changed(self, name: str) -> None:
        """Load CRUISE_HEADER + default EVENT_HEADER from selected template."""
        if not name or name in ("No templates found", "---"):
            self._clear_cruise_header_fields()
            self._clear_event_header_fields()
            return

        template = self._mission_templates.get(name, {})
        cruise = template.get("cruise_header", {})
        event_defaults = self._mission_templates.get("event_header", {})

        cruise_field_map = {
            "country_institute_code": self.ui.countryInstituteCodeLineEdit,
            "cruise_number":          self.ui.cruiseNumberLineEdit,
            "organization":           self.ui.organizationLineEdit,
            "chief_scientist":        self.ui.chiefScientistLineEdit,
            "cruise_name":            self.ui.cruiseNameLineEdit,
            "platform":               self.ui.platformLineEdit,
            "start_date":             self.ui.startDateLineEdit,
            "end_date":               self.ui.endDateLineEdit,
            "cruise_description":     self.ui.cruiseDescriptionLineEdit,
        }

        event_field_map = {
            "data_type":              self.ui.dataTypeLineEdit,
            "event_number":           self.ui.eventNumberLineEdit,
            "event_qualifier1":       self.ui.eventQualifier1LineEdit,
            "event_qualifier2":       self.ui.eventQualifier2LineEdit,
            "creation_date":          self.ui.creationDateLineEdit,
            "orig_creation_date":     self.ui.origCreationDateLineEdit,
            "start_date_time":        self.ui.startDateTimeLineEdit,
            "end_date_time":          self.ui.endDateTimeLineEdit,
            "initial_latitude":       self.ui.initialLatitudeLineEdit,
            "initial_longitude":      self.ui.initialLongitudeLineEdit,
            "end_latitude":           self.ui.endLatitudeLineEdit,
            "end_longitude":          self.ui.endLongitudeLineEdit,
            "min_depth":              self.ui.minDepthLineEdit,
            "max_depth":              self.ui.maxDepthLineEdit,
            "sampling_interval":      self.ui.samplingIntervalLineEdit,
            "sounding":               self.ui.soundingLineEdit,
            "depth_off_bottom":       self.ui.depthOffBottomLineEdit,
            "station_name":           self.ui.stationNameLineEdit,
            "set_number":             self.ui.setNumberLineEdit,
            "event_comments":         self.ui.eventCommentsLineEdit,
        }

        # Block signals while populating
        for w in list(cruise_field_map.values()) + list(event_field_map.values()):
            w.blockSignals(True)
        try:
            for key, w in cruise_field_map.items():
                w.setText(str(cruise.get(key, "") or ""))
            # EVENT defaults:
            for key, w in event_field_map.items():
                w.setText(str(event_defaults.get(key, "") or ""))
        finally:
            for w in list(cruise_field_map.values()) + list(event_field_map.values()):
                w.blockSignals(False)

        # Update some fields based on year entered
        year = self.ui.yearLineEdit.text()
        cn = self.ui.cruiseNumberLineEdit.text()
        if cn.startswith('BCD'):
            mission_code = cn[7:]
            new_cn = f'BCD{year}{mission_code}'
            self.ui.cruiseNumberLineEdit.setText(new_cn)
            start_date = f'01-JAN-{year} 00:00:00.00'
            end_date = f'31-DEC-{year} 00:00:00.00'
            self.ui.startDateLineEdit.setText(start_date)
            self.ui.endDateLineEdit.setText(end_date)

            # Update the station name if template is for a fixed station
            toks = name.split(" ")
            station_name = toks[2]
            if station_name == 'BBMP':
                station_name = 'HL_00'
            self.ui.stationNameLineEdit.setText(station_name)

    # -----------------------------
    # Data collection & actions
    # -----------------------------
    def _parse_datetime(self, widget, label: str):
        """
        Parse a date/time from a QLineEdit using check_datetime.
        Raises a ValueError with a labeled, machine-parseable message on failure.
        """
        text = widget.text().strip()
        try:
            return check_datetime(text)
        except ValueError as e:
            # Prefix with a tag so the caller can distinguish categories:
            #   [DATETIME] <Label>: <original message>
            raise ValueError(f"[DATETIME] {label}: {e}") from e

    def _parse_float(self, widget, label: str):
        """
        Parse a float from a QLineEdit. Uses Python float() for semantic validation.
        QDoubleValidator only ensures format while editing; we still need a final parse.
        Raises a ValueError with a labeled, machine-parseable message on failure.
        """
        text = widget.text().strip()
        if text == "":
            # If empty is allowed, decide policy: either return None or treat as error.
            # Here we treat empty as error to force explicit input.
            return BaseHeader.NULL_VALUE
            # raise ValueError(f"[FLOAT] {label}: value is required")
        try:
            return float(text)
        except ValueError as e:
            raise ValueError(f"[FLOAT] {label}: {e}") from e

    def collect_metadata(self) -> OdfHeader:
        """Create and fill an OdfHeader from current UI values."""
        odf = OdfHeader()

        # CRUISE_HEADER
        odf.cruise_header.country_institute_code = self.ui.countryInstituteCodeLineEdit.text()
        odf.cruise_header.cruise_number = self.ui.cruiseNumberLineEdit.text()
        odf.cruise_header.organization = self.ui.organizationLineEdit.text()
        odf.cruise_header.chief_scientist = self.ui.chiefScientistLineEdit.text()
        odf.cruise_header.start_date = self.ui.startDateLineEdit.text()
        odf.cruise_header.end_date = self.ui.endDateLineEdit.text()
        odf.cruise_header.platform = self.ui.platformLineEdit.text()
        odf.cruise_header.cruise_name = self.ui.cruiseNameLineEdit.text()
        odf.cruise_header.cruise_description = self.ui.cruiseDescriptionLineEdit.text()

        # EVENT_HEADER
        odf.event_header.data_type = self.ui.dataTypeLineEdit.text()
        odf.event_header.event_number = self.ui.eventNumberLineEdit.text()
        odf.event_header.event_qualifier1 = self.ui.eventQualifier1LineEdit.text()
        odf.event_header.event_qualifier2 = self.ui.eventQualifier2LineEdit.text()

        # Dates — parsed (will raise [DATETIME] ValueError on error)
        odf.event_header.creation_date = self._parse_datetime(self.ui.creationDateLineEdit, "Creation Date")
        odf.event_header.orig_creation_date = self._parse_datetime(self.ui.origCreationDateLineEdit, "Original Creation Date")
        odf.event_header.start_date_time = self._parse_datetime(self.ui.startDateTimeLineEdit, "Start Date/Time")
        odf.event_header.end_date_time = self._parse_datetime(self.ui.endDateTimeLineEdit, "End Date/Time")

        # cdate = check_datetime(self.ui.creationDateLineEdit.text())
        # odf.event_header.creation_date = cdate
        # ocdate = check_datetime(self.ui.origCreationDateLineEdit.text())  # pull from the correct field
        # odf.event_header.orig_creation_date = ocdate
        # odf.event_header.start_date_time = check_datetime(self.ui.startDateTimeLineEdit.text())
        # odf.event_header.end_date_time = check_datetime(self.ui.endDateTimeLineEdit.text())

        # odf.event_header.initial_latitude = self.ui.initialLatitudeLineEdit.text()
        # odf.event_header.initial_longitude = self.ui.initialLongitudeLineEdit.text()
        # odf.event_header.end_latitude = self.ui.endLatitudeLineEdit.text()
        # odf.event_header.end_longitude = self.ui.endLongitudeLineEdit.text()
        # odf.event_header.min_depth = self.ui.minDepthLineEdit.text()
        # odf.event_header.max_depth = self.ui.maxDepthLineEdit.text()
        # odf.event_header.sampling_interval = self.ui.samplingIntervalLineEdit.text()
        # odf.event_header.sounding = self.ui.soundingLineEdit.text()
        # odf.event_header.depth_off_bottom = self.ui.depthOffBottomLineEdit.text()
        # odf.event_header.station_name = self.ui.stationNameLineEdit.text()
        # odf.event_header.set_number = self.ui.setNumberLineEdit.text()
        # odf.event_header.event_comments = [self.ui.eventCommentsLineEdit.text()]

        # Floats — parsed (will raise [FLOAT] ValueError on error)
        # If some are optional, adjust _parse_float to allow empty and return None
        odf.event_header.initial_latitude = self._parse_float(self.ui.initialLatitudeLineEdit, "Initial Latitude")
        odf.event_header.initial_longitude = self._parse_float(self.ui.initialLongitudeLineEdit, "Initial Longitude")
        odf.event_header.end_latitude = self._parse_float(self.ui.endLatitudeLineEdit, "End Latitude")
        odf.event_header.end_longitude = self._parse_float(self.ui.endLongitudeLineEdit, "End Longitude")
        odf.event_header.min_depth = self._parse_float(self.ui.minDepthLineEdit, "Min Depth")
        odf.event_header.max_depth = self._parse_float(self.ui.maxDepthLineEdit, "Max Depth")
        odf.event_header.sampling_interval = self._parse_float(self.ui.samplingIntervalLineEdit, "Sampling Interval")
        odf.event_header.sounding = self._parse_float(self.ui.soundingLineEdit, "Sounding")
        odf.event_header.depth_off_bottom = self._parse_float(self.ui.depthOffBottomLineEdit, "Depth Off Bottom")

        # Remaining strings
        odf.event_header.station_name = self.ui.stationNameLineEdit.text()
        odf.event_header.set_number = self.ui.setNumberLineEdit.text()
        odf.event_header.event_comments = [self.ui.eventCommentsLineEdit.text()]

        return odf

    @Slot()
    def export_to_odf(self) -> None:
        """Example action: build and print the header (replace with real writer)."""
        odf = self.collect_metadata()
        print(odf.print_object())

    # -----------------------------
    # Button handlers (emit signals)
    # -----------------------------
    @Slot()
    def _on_ok_clicked(self):
        try:
            odf = self.collect_metadata()
        except ValueError as e:
            msg = str(e)

            # Decide category; default title is generic
            title = "Invalid input"
            if msg.startswith("[DATETIME]"):
                title = "Invalid date/time"
            elif msg.startswith("[FLOAT]"):
                title = "Invalid numeric value"

            # Show message
            QMessageBox.warning(self.window() or self, title, msg)

            # Smart focus: locate the field by label within the message
            # Map labels used in _parse_* to widgets
            label_to_widget = {
                "Creation Date": self.ui.creationDateLineEdit,
                "Original Creation Date": self.ui.origCreationDateLineEdit,
                "Start Date/Time": self.ui.startDateTimeLineEdit,
                "End Date/Time": self.ui.endDateTimeLineEdit,
                "Initial Latitude": self.ui.initialLatitudeLineEdit,
                "Initial Longitude": self.ui.initialLongitudeLineEdit,
                "End Latitude": self.ui.endLatitudeLineEdit,
                "End Longitude": self.ui.endLongitudeLineEdit,
                "Min Depth": self.ui.minDepthLineEdit,
                "Max Depth": self.ui.maxDepthLineEdit,
                "Sampling Interval": self.ui.samplingIntervalLineEdit,
                "Sounding": self.ui.soundingLineEdit,
                "Depth Off Bottom": self.ui.depthOffBottomLineEdit,
            }
            for label, w in label_to_widget.items():
                if label in msg:
                    w.setFocus()
                    w.selectAll()
                    break

            return  # Keep dialog open so the user can fix it

        # Success path
        self.submitted.emit(odf)

    @Slot()
    def _on_cancel_clicked(self):
        self.cancelled.emit()
    