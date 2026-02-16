import json
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QLocale, QTimer, Signal, Slot
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import QMessageBox, QWidget

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.validated_base import check_datetime

# You need to run the following command to generate the ui_odf_metadata_form.py file:
#     pyside6-uic odf_metadata_form.ui -o ui_odf_metadata_form.py
from .ui_odf_metadata_form import Ui_odf_metadata_form


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
        self.ui = Ui_odf_metadata_form()

        self.ui.setupUi(self)

        # ---- 2) Init state and helpers ----

        # Get a Path-like object to a file inside the package
        template_file = files("datashop_toolbox") / "gui" / "templates" / "mission_header_templates.json"
        self._mission_templates_path = mission_templates_path or template_file
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
        self.ui.year_line_edit.setPlaceholderText("####")
        self.ui.initial_latitude_line_edit.setPlaceholderText("####.######")
        self.ui.initial_longitude_line_edit.setPlaceholderText("####.######")
        self.ui.end_latitude_line_edit.setPlaceholderText("####.######")
        self.ui.end_longitude_line_edit.setPlaceholderText("####.######")
        self.ui.min_depth_line_edit.setPlaceholderText("####.##")
        self.ui.max_depth_line_edit.setPlaceholderText("####.##")
        self.ui.sampling_interval_line_edit.setPlaceholderText("####.####")
        self.ui.sounding_line_edit.setPlaceholderText("####.##")
        self.ui.depth_off_bottom_line_edit.setPlaceholderText("####.##")

        year_validator = QIntValidator(1900, 2050)
        latitude_validator = QDoubleValidator(-90.0, 90.0, 6)
        longitude_validator = QDoubleValidator(-180.0, 180.0, 6)
        depth_validator = QDoubleValidator(0.0, 6000.0, 2)
        sample_interval_validator = QDoubleValidator(0.0, 1000.0, 4)

        locale = QLocale(QLocale.English, QLocale.UnitedStates)
        for v in (latitude_validator, longitude_validator, depth_validator, sample_interval_validator):
            v.setLocale(locale)
            v.setNotation(QDoubleValidator.StandardNotation)
        
        # Apply to fields (note: end_latitude uses latitude validator)
        self.ui.year_line_edit.setValidator(year_validator)
        self.ui.initial_latitude_line_edit.setValidator(latitude_validator)
        self.ui.initial_longitude_line_edit.setValidator(longitude_validator)
        self.ui.end_latitude_line_edit.setValidator(latitude_validator)
        self.ui.end_longitude_line_edit.setValidator(longitude_validator)
        self.ui.min_depth_line_edit.setValidator(depth_validator)
        self.ui.max_depth_line_edit.setValidator(depth_validator)
        self.ui.sampling_interval_line_edit.setValidator(sample_interval_validator)
        self.ui.sounding_line_edit.setValidator(depth_validator)
        self.ui.depth_off_bottom_line_edit.setValidator(depth_validator)

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
            self.ui.mission_template_selector_combo_box.clear()
            self.ui.mission_template_selector_combo_box.addItem("No templates found")
            return

        keys = list(self._mission_templates.keys())
        # Hide the shared section (if present) from the selector
        if "event_header" in keys:
            keys.remove("event_header")
        # Insert '---' on top as a "no selection"
        keys.insert(0, "---")

        self.ui.mission_template_selector_combo_box.clear()
        self.ui.mission_template_selector_combo_box.addItems(keys)

    def _populate_year(self):
        # Populate year with current year
        self.ui.year_line_edit.setText(str(datetime.now().year))

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

    # def showEvent(self, event):
    #     """Overrides the show event to run code after the dialog is visible."""
    #     super().showEvent(event)  # Call base class handler
    #     # Populate year now
    #     self._on_dialog_visible()
    #     # Show warning AFTER the parent dialog is exposed
    #     self._show_warning_dialog()

    def _on_dialog_visible(self):
        """Function that runs when the dialog appears."""
        # Perform tasks like loading data, starting animations, etc.
        self._populate_year()

    def _connect_signals(self):
        self.ui.mission_template_selector_combo_box.currentTextChanged.connect(self._on_template_changed)
        # Your UI provides dedicated OK/Cancel buttons on the form
        self.ui.ok_push_button.clicked.connect(self._on_ok_clicked)
        self.ui.cancel_push_button.clicked.connect(self._on_cancel_clicked)

    # -----------------------------
    # Template loading
    # -----------------------------
    def _clear_cruise_header_fields(self):
        for w in (
            self.ui.country_institute_code_line_edit,
            self.ui.cruise_number_line_edit,
            self.ui.organization_line_edit,
            self.ui.chief_scientist_line_edit,
            self.ui.start_date_line_edit,
            self.ui.end_date_line_edit,
            self.ui.platform_line_edit,
            self.ui.cruise_name_line_edit,
            self.ui.cruise_description_line_edit,  # correct attribute name in UI  # noqa
        ):
            w.clear()

    def _clear_event_header_fields(self):
        for w in (
            self.ui.data_type_line_edit,
            self.ui.event_number_line_edit,
            self.ui.event_qualifier1_line_edit,
            self.ui.event_qualifier2_line_edit,
            self.ui.creation_date_line_edit,
            self.ui.orig_creation_date_line_edit,
            self.ui.start_date_time_line_edit,
            self.ui.end_date_time_line_edit,
            self.ui.initial_latitude_line_edit,
            self.ui.initial_longitude_line_edit,
            self.ui.end_latitude_line_edit,
            self.ui.end_longitude_line_edit,
            self.ui.min_depth_line_edit,
            self.ui.max_depth_line_edit,
            self.ui.sampling_interval_line_edit,
            self.ui.sounding_line_edit,
            self.ui.depth_off_bottom_line_edit,
            self.ui.station_name_line_edit,
            self.ui.set_number_line_edit,
            self.ui.event_comments_line_edit,
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
            "country_institute_code": self.ui.country_institute_code_line_edit,
            "cruise_number":          self.ui.cruise_number_line_edit,
            "organization":           self.ui.organization_line_edit,
            "chief_scientist":        self.ui.chief_scientist_line_edit,
            "cruise_name":            self.ui.cruise_name_line_edit,
            "platform":               self.ui.platform_line_edit,
            "start_date":             self.ui.start_date_line_edit,
            "end_date":               self.ui.end_date_line_edit,
            "cruise_description":     self.ui.cruise_description_line_edit,
        }

        event_field_map = {
            "data_type":              self.ui.data_type_line_edit,
            "event_number":           self.ui.event_number_line_edit,
            "event_qualifier1":       self.ui.event_qualifier1_line_edit,
            "event_qualifier2":       self.ui.event_qualifier2_line_edit,
            "creation_date":          self.ui.creation_date_line_edit,
            "orig_creation_date":     self.ui.orig_creation_date_line_edit,
            "start_date_time":        self.ui.start_date_time_line_edit,
            "end_date_time":          self.ui.end_date_time_line_edit,
            "initial_latitude":       self.ui.initial_latitude_line_edit,
            "initial_longitude":      self.ui.initial_longitude_line_edit,
            "end_latitude":           self.ui.end_latitude_line_edit,
            "end_longitude":          self.ui.end_longitude_line_edit,
            "min_depth":              self.ui.min_depth_line_edit,
            "max_depth":              self.ui.max_depth_line_edit,
            "sampling_interval":      self.ui.sampling_interval_line_edit,
            "sounding":               self.ui.sounding_line_edit,
            "depth_off_bottom":       self.ui.depth_off_bottom_line_edit,
            "station_name":           self.ui.station_name_line_edit,
            "set_number":             self.ui.set_number_line_edit,
            "event_comments":         self.ui.event_comments_line_edit,
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
        year = self.ui.year_line_edit.text()
        cn = self.ui.cruise_number_line_edit.text()
        if cn.startswith('BCD'):
            mission_code = cn[7:]
            new_cn = f'BCD{year}{mission_code}'
            self.ui.cruise_number_line_edit.setText(new_cn)
            start_date = f'01-JAN-{year} 00:00:00.00'
            end_date = f'31-DEC-{year} 00:00:00.00'
            self.ui.start_date_line_edit.setText(start_date)
            self.ui.end_date_line_edit.setText(end_date)

            # Update the station name if template is for a fixed station
            toks = name.split(" ")
            station_name = toks[2]
            if station_name == 'BBMP':
                station_name = 'HL_00'
            self.ui.station_name_line_edit.setText(station_name)

    # -----------------------------
    # Data collection & actions
    # -----------------------------
    def _parse_datetime(self, widget, label: str):
        """
        Parse a date/time from a Q_line_edit using check_datetime.
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
        Parse a float from a Q_line_edit. Uses Python float() for semantic validation.
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
        odf.cruise_header.country_institute_code = self.ui.country_institute_code_line_edit.text()
        odf.cruise_header.cruise_number = self.ui.cruise_number_line_edit.text()
        odf.cruise_header.organization = self.ui.organization_line_edit.text()
        odf.cruise_header.chief_scientist = self.ui.chief_scientist_line_edit.text()
        odf.cruise_header.start_date = self.ui.start_date_line_edit.text()
        odf.cruise_header.end_date = self.ui.end_date_line_edit.text()
        odf.cruise_header.platform = self.ui.platform_line_edit.text()
        odf.cruise_header.cruise_name = self.ui.cruise_name_line_edit.text()
        odf.cruise_header.cruise_description = self.ui.cruise_description_line_edit.text()

        # EVENT_HEADER
        odf.event_header.data_type = self.ui.data_type_line_edit.text()
        odf.event_header.event_number = self.ui.event_number_line_edit.text()
        odf.event_header.event_qualifier1 = self.ui.event_qualifier1_line_edit.text()
        odf.event_header.event_qualifier2 = self.ui.event_qualifier2_line_edit.text()

        # Dates — parsed (will raise [DATETIME] ValueError on error)
        odf.event_header.creation_date = self._parse_datetime(self.ui.creation_date_line_edit, "Creation Date")
        odf.event_header.orig_creation_date = self._parse_datetime(self.ui.orig_creation_date_line_edit, "Original Creation Date")
        odf.event_header.start_date_time = self._parse_datetime(self.ui.start_date_time_line_edit, "Start Date/Time")
        odf.event_header.end_date_time = self._parse_datetime(self.ui.end_date_time_line_edit, "End Date/Time")

        # cdate = check_datetime(self.ui.creation_date_line_edit.text())
        # odf.event_header.creation_date = cdate
        # ocdate = check_datetime(self.ui.orig_creation_date_line_edit.text())  # pull from the correct field
        # odf.event_header.orig_creation_date = ocdate
        # odf.event_header.start_date_time = check_datetime(self.ui.start_date_time_line_edit.text())
        # odf.event_header.end_date_time = check_datetime(self.ui.end_date_time_line_edit.text())

        # odf.event_header.initial_latitude = self.ui.initial_latitude_line_edit.text()
        # odf.event_header.initial_longitude = self.ui.initial_longitude_line_edit.text()
        # odf.event_header.end_latitude = self.ui.end_latitude_line_edit.text()
        # odf.event_header.end_longitude = self.ui.end_longitude_line_edit.text()
        # odf.event_header.min_depth = self.ui.min_depth_line_edit.text()
        # odf.event_header.max_depth = self.ui.max_depth_line_edit.text()
        # odf.event_header.sampling_interval = self.ui.sampling_interval_line_edit.text()
        # odf.event_header.sounding = self.ui.sounding_line_edit.text()
        # odf.event_header.depth_off_bottom = self.ui.depth_off_bottom_line_edit.text()
        # odf.event_header.station_name = self.ui.station_name_line_edit.text()
        # odf.event_header.set_number = self.ui.set_number_line_edit.text()
        # odf.event_header.event_comments = [self.ui.event_comments_line_edit.text()]

        # Floats — parsed (will raise [FLOAT] ValueError on error)
        # If some are optional, adjust _parse_float to allow empty and return None
        odf.event_header.initial_latitude = self._parse_float(self.ui.initial_latitude_line_edit, "Initial Latitude")
        odf.event_header.initial_longitude = self._parse_float(self.ui.initial_longitude_line_edit, "Initial Longitude")
        odf.event_header.end_latitude = self._parse_float(self.ui.end_latitude_line_edit, "End Latitude")
        odf.event_header.end_longitude = self._parse_float(self.ui.end_longitude_line_edit, "End Longitude")
        odf.event_header.min_depth = self._parse_float(self.ui.min_depth_line_edit, "Min Depth")
        odf.event_header.max_depth = self._parse_float(self.ui.max_depth_line_edit, "Max Depth")
        odf.event_header.sampling_interval = self._parse_float(self.ui.sampling_interval_line_edit, "Sampling Interval")
        odf.event_header.sounding = self._parse_float(self.ui.sounding_line_edit, "Sounding")
        odf.event_header.depth_off_bottom = self._parse_float(self.ui.depth_off_bottom_line_edit, "Depth Off Bottom")

        # Remaining strings
        odf.event_header.station_name = self.ui.station_name_line_edit.text()
        odf.event_header.set_number = self.ui.set_number_line_edit.text()
        odf.event_header.event_comments = [self.ui.event_comments_line_edit.text()]

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
                "Creation Date": self.ui.creation_date_line_edit,
                "Original Creation Date": self.ui.orig_creation_date_line_edit,
                "Start Date/Time": self.ui.start_date_time_line_edit,
                "End Date/Time": self.ui.end_date_time_line_edit,
                "Initial Latitude": self.ui.initial_latitude_line_edit,
                "Initial Longitude": self.ui.initial_longitude_line_edit,
                "End Latitude": self.ui.end_latitude_line_edit,
                "End Longitude": self.ui.end_longitude_line_edit,
                "Min Depth": self.ui.min_depth_line_edit,
                "Max Depth": self.ui.max_depth_line_edit,
                "Sampling Interval": self.ui.sampling_interval_line_edit,
                "Sounding": self.ui.sounding_line_edit,
                "Depth Off Bottom": self.ui.depth_off_bottom_line_edit,
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
    