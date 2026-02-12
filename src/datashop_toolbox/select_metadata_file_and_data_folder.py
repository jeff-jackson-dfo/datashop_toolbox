import json
import re
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

BASE_DIR = Path(__file__).resolve().parent
meta_dir = BASE_DIR / "temporary"
meta_dir.mkdir(parents=True, exist_ok=True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.meta_store_path = meta_dir / ".mtr_last_user_metadata.json"
        self.setWindowTitle("MTR Processing Toolbox - ODF Generator")
        self.resize(750, 480)

        self.line_edit_text = ""
        self.institution = "BIO"
        self.instrument = "Minilog"
        self.metadata_file = ""
        self.input_data_folder = ""
        self.output_data_folder = ""
        self.result = None
        self.user_input_meta = {}
        self.remember_input_dict = {}
        self.remember_input_choice = False

        # --- Data Processor Name ---
        self.line_edit_title = QLabel(
            "Please enter the data processor's name in the text box below:"
        )
        self.line_edit = QLineEdit()
        self.line_edit.setFixedHeight(25)
        font = self.line_edit_title.font()
        font.setPointSize(11)
        self.line_edit_title.setFont(font)
        self.line_edit_title.setFixedHeight(25)
        self.line_edit.setFont(font)
        self.line_edit.editingFinished.connect(self.editing_finished)

        self.remember_meta_checkbox = QCheckBox("Remember last user metadata")
        self.remember_meta_checkbox.setChecked(self.remember_input_choice)

        # --- Institution Combo ---
        self.institution_combo_label = QLabel("Select institution:")
        self.institution_combo_label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        self.institution_combo_label.setFixedSize(225, 15)
        self.institution_combo = QComboBox()
        self.institution_combo.addItems(["BIO", "FSRS"])
        self.institution_combo.currentTextChanged.connect(
            self.institution_text_changed
        )  # Sends the current text (string) of the selected item.
        self.institution_combo.setCurrentIndex(0)

        # --- Instrument Combo ---
        self.instrument_combo_label = QLabel("Select instrument:")
        self.instrument_combo_label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        self.instrument_combo_label.setFixedSize(225, 15)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(["Minilog", "Hobo"])
        self.instrument_combo.currentTextChanged.connect(
            self.instrument_text_changed
        )  # Sends the current text (string) of the selected item.
        self.instrument_combo.setCurrentIndex(0)

        # --- Cruise Header Fields ---
        self.organization_label = QLabel("Organization:")
        self.organization_input = QLineEdit()
        self.chiefscientist_label = QLabel("Chief Scientist:")
        self.chiefscientist_input = QLineEdit()
        self.cruisedesc_label = QLabel("Cruise Description:")
        self.cruisedesc_input = QLineEdit()
        self.platform_label = QLabel("Platform Name:")
        self.platform_input = QLineEdit()
        self.country_label = QLabel("Country Instuition Code:")
        self.country_input = QLineEdit()
        self.cruise_number_label = QLabel("Cruise Number:")
        self.cruise_number_input = QLineEdit()

        # Load last user metadata if available"
        self.load_last_user_metadata()

        # --- Buttons for Metadata + Data Folder ---
        self.file_button = QPushButton(
            "Select meta data file\n(e.g. LFA .txt file, \nor Excel file)"
        )
        self.file_button.setFixedSize(225, 100)
        font = self.file_button.font()
        font.setPointSize(11)
        font.setBold(True)
        self.file_button.setFont(font)
        self.file_button.setStyleSheet("font-weight: bold;")
        self.file_button.clicked.connect(self.choose_metadata_file)

        self.input_data_folder_button = QPushButton(
            "Select input data folder\n(Location of raw *.csv files)"
        )
        self.input_data_folder_button.setFixedSize(225, 100)
        font = self.input_data_folder_button.font()
        font.setPointSize(11)
        font.setBold(True)
        self.input_data_folder_button.setFont(font)
        self.input_data_folder_button.setStyleSheet("font-weight: bold;")
        self.input_data_folder_button.clicked.connect(self.choose_input_data_folder)

        self.output_data_folder_button = QPushButton(
            "Select output data folder\n(Location for *.odf files)"
        )
        self.output_data_folder_button.setFixedSize(225, 100)
        font = self.output_data_folder_button.font()
        font.setPointSize(11)
        font.setBold(True)
        self.output_data_folder_button.setFont(font)
        self.output_data_folder_button.setStyleSheet("font-weight: bold;")
        self.output_data_folder_button.clicked.connect(self.choose_output_data_folder)

        # --- Dialog Buttons ---
        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

        # --- Selection of data folder and meta data ---
        self.metadata_file_label = QLabel("Metadata file selected:")
        self.metadata_file_path_text = QLineEdit(" ")
        self.metadata_file_path_text.setFixedWidth(600)
        # font.setPointSize(9)
        self.metadata_file_label.setFont(font)
        self.metadata_file_label.setFixedHeight(25)
        self.metadata_file_path_text.setFixedHeight(25)

        self.input_data_folder_label = QLabel("Input data folder selected:")
        self.input_data_folder_path_text = QLineEdit(" ")
        self.input_data_folder_path_text.setFixedWidth(600)
        self.input_data_folder_label.setFont(font)
        self.input_data_folder_label.setFixedHeight(25)
        self.input_data_folder_path_text.setFixedHeight(25)

        self.output_data_folder_label = QLabel("Output data folder selected:")
        self.output_data_folder_path_text = QLineEdit(" ")
        self.output_data_folder_path_text.setFixedWidth(600)
        self.output_data_folder_label.setFont(font)
        self.output_data_folder_label.setFixedHeight(25)
        self.output_data_folder_path_text.setFixedHeight(25)

        title_layout = QHBoxLayout()
        title_layout.addWidget(self.line_edit_title)
        title_layout.addStretch()  # push checkbox to the right
        title_layout.addWidget(self.remember_meta_checkbox)

        # Vertical layout for label + line edit
        v_layout1 = QVBoxLayout()
        v_layout1.addLayout(title_layout)
        # v_layout1.addWidget(self.line_edit_title)
        v_layout1.addWidget(self.line_edit)

        # Vertical layout for institution label + combo box
        v_layout2_1 = QVBoxLayout()
        v_layout2_1.addWidget(self.institution_combo_label)
        v_layout2_1.addWidget(self.institution_combo)

        # Vertical layout for instrument label + combo box
        v_layout2_2 = QVBoxLayout()
        v_layout2_2.addWidget(self.instrument_combo_label)
        v_layout2_2.addWidget(self.instrument_combo)

        # Horizontal layout for combo boxes and their labels
        h_layout_1 = QHBoxLayout()
        h_layout_1.addLayout(v_layout2_1)
        h_layout_1.addLayout(v_layout2_2)
        v_layout1.addLayout(h_layout_1)

        # Cruise header fields
        cruise_header_layout = QVBoxLayout()
        cruise_header_layout.setSpacing(2)
        cruise_header_layout.setContentsMargins(0, 5, 0, 5)
        title_label = QLabel("User Meta Info:")
        title_label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        cruise_header_layout.addWidget(title_label)

        self.organization_label.setFixedWidth(140)
        self.chiefscientist_label.setFixedWidth(140)
        self.cruisedesc_label.setFixedWidth(140)
        self.platform_label.setFixedWidth(140)
        self.country_label.setFixedWidth(140)
        self.cruise_number_label.setFixedWidth(140)

        for label, widget in [
            (self.organization_label, self.organization_input),
            (self.chiefscientist_label, self.chiefscientist_input),
            (self.cruisedesc_label, self.cruisedesc_input),
            (self.platform_label, self.platform_input),
            (self.country_label, self.country_input),
            (self.cruise_number_label, self.cruise_number_input),
        ]:
            row = QHBoxLayout()
            row.setSpacing(5)
            row.addWidget(label)
            row.addWidget(widget)
            cruise_header_layout.addLayout(row)
        v_layout1.addLayout(cruise_header_layout)

        # Horizontal layout for buttons to open file and folder dialogs
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(self.file_button)
        h_layout2.addWidget(self.input_data_folder_button)
        h_layout2.addWidget(self.output_data_folder_button)
        v_layout1.addLayout(h_layout2)

        # Horizontal layout for label and lineedit containing selected file
        h_layout3 = QHBoxLayout()
        h_layout3.addWidget(self.metadata_file_label)
        h_layout3.addWidget(self.metadata_file_path_text)

        # Horizontal layout for label and lineedit containing selected folder path
        h_layout4 = QHBoxLayout()
        h_layout4.addWidget(self.input_data_folder_label)
        h_layout4.addWidget(self.input_data_folder_path_text)
        h_layout5 = QHBoxLayout()
        h_layout5.addWidget(self.output_data_folder_label)
        h_layout5.addWidget(self.output_data_folder_path_text)

        v_layout4 = QVBoxLayout()
        v_layout4.addLayout(h_layout3)
        v_layout4.addLayout(h_layout4)
        v_layout4.addLayout(h_layout5)
        v_layout1.addLayout(v_layout4)

        # Horizontal layout for buttons used to close the window
        h_layout6 = QHBoxLayout()
        h_layout6.addStretch(1)
        h_layout6.addWidget(self.buttonBox)
        h_layout6.addStretch(1)
        v_layout1.addLayout(h_layout6)

        # Set the central widget of the Window.
        container = QWidget()
        container.setLayout(v_layout1)
        self.setCentralWidget(container)

    def editing_finished(self):
        text = self.line_edit.text().strip()
        if not text:
            return
        self.line_edit_text = text
        print("\n========== MTR Data Processing Inputs ==========")
        print(f"\n(1 of 4) Data processor: {self.line_edit_text}\n")

    def institution_text_changed(self, s):
        self.institution = s
        if s == "BIO":
            # Allow both instruments
            self.instrument_combo.clear()
            self.instrument_combo.addItems(["Minilog", "Hobo"])
            self.instrument_combo.setCurrentIndex(0)
        elif s == "FSRS":
            # FSRS only supports Minilog
            self.instrument_combo.clear()
            self.instrument_combo.addItem("Minilog")
            self.instrument = "Minilog"  # ensure consistency
        # Update cruise header defaults
        self.populate_defaults(s)

    def instrument_text_changed(self, s):
        self.instrument = s

    def find_raw_data_folder(self, base_dir):
        """
        Search for a folder containing 'raw' in its name (case-insensitive)
        inside base_dir.
        """
        keywords = ["raw", "csv", "input"]
        for p in base_dir.iterdir():
            if p.is_dir() and any(keyword in p.name.lower() for keyword in keywords):
                return p
        return None

    def choose_metadata_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select the Metadata file")
        if not file_path:
            return
        if file_path:
            self.metadata_file = file_path
            self.metadata_file_path_text.setText(self.metadata_file)
            print(f"\n(2 of 4) Metadata file chosen: {file_path}\n")
            meta_path = Path(file_path)
            meta_dir = meta_path.parent
            raw_folder = self.find_raw_data_folder(meta_dir)
            if raw_folder:
                self.input_data_folder = str(raw_folder)
                self.input_data_folder_path_text.setText(self.input_data_folder)

                print(f"(3 of 4) Input data folder auto-detected: {self.input_data_folder}")
            else:
                print(
                    "⚠️ No Raw data folder found near metadata file. "
                    "Please select input folder manually."
                )

            self.output_data_folder = str(meta_dir)
            self.output_data_folder_path_text.setText(self.output_data_folder)
            print(f"(4 of 4) Output data folder auto-set to: {self.output_data_folder}\n")

    def choose_input_data_folder(self):
        input_folder_path = QFileDialog.getExistingDirectory(self, "Select the input data folder")
        if input_folder_path:
            self.input_data_folder = input_folder_path
            print(f"\n(3 of 4) Input data file folder selected: {input_folder_path}\n")
            self.input_data_folder_path_text.setText(self.input_data_folder)

    def choose_output_data_folder(self):
        output_folder_path = QFileDialog.getExistingDirectory(self, "Select the output data folder")
        if output_folder_path:
            self.output_data_folder = output_folder_path
            print(f"\n(4 of 4) output data file folder selected: {output_folder_path}\n")
            self.output_data_folder_path_text.setText(self.output_data_folder)

    def on_accept(self):
        self.result = "accept"
        processor_name = self.line_edit.text().strip()
        # Read text from the Cruise Header input fields
        organization = self.organization_input.text().strip()
        chief_scientist = self.chiefscientist_input.text().strip()
        cruise_desc = self.cruisedesc_input.text().strip()
        platform_name = self.platform_input.text().strip()
        country_code = self.country_input.text().strip()
        cruise_number_code = self.cruise_number_input.text().strip()

        self.user_input_meta = {
            "organization": organization,
            "chief_scientist": chief_scientist,
            "cruise_description": cruise_desc,
            "platform_name": platform_name,
            "country_code": country_code,
            "cruise_number": cruise_number_code,
        }
        if self.remember_meta_checkbox.isChecked():
            self.remember_input_choice = True
            self.remember_input_dict = {
                "input_choice": self.remember_input_choice,
                "processor_name": processor_name,
                "institution": self.institution,
                "instrument": self.instrument,
                "default_user_meta": self.user_input_meta,
            }
            self.save_last_user_metadata()
        else:
            self.clear_last_user_metadata()
            self.remember_input_choice = False
            self.remember_input_dict = {}
        self.close()
        # self.hide()

    def on_reject(self):
        self.result = "reject"
        self.close()

    def save_last_user_metadata(self):
        try:
            with Path.open(self.meta_store_path, "w", encoding="utf-8") as f:
                json.dump(self.remember_input_dict, f, indent=4)
            print("💾 User metadata saved")
        except Exception as e:
            print(f"❌ Failed to save metadata: {e}")

    def clear_last_user_metadata(self):
        try:
            if self.meta_store_path.exists():
                self.meta_store_path.unlink()
                print("🗑️ Cleared saved user metadata")
        except Exception as e:
            print(f"❌ Failed to clear metadata: {e}")

    def populate_defaults(self, institution):
        """Populate 4 fields based on institution selection."""
        if institution == "BIO":
            self.organization_input.setText("DFO BIO")
            self.chiefscientist_input.setText("ADAM DROZDOWSKI")
            self.cruisedesc_input.setText("LONG TERM TEMPERATURE MONITORING PROGRAM (LTTMP)")
            self.platform_input.setText("BIO CRUISE DATA (NO ICES CODE)")
            self.country_input.setText("1810")
            self.cruise_number_input.setPlaceholderText(
                "if known use the format (BCDcruise_year999) else leave blank"
            )
        elif institution == "FSRS":
            self.organization_input.setText("FSRS")
            self.chiefscientist_input.setText("SHANNON SCOTT-TIBBETTS")
            self.cruisedesc_input.setText("FISHERMEN  AND SCIENTISTS RESEARCH SOCIETY")
            self.platform_input.setText("FSRS CRUISE DATA (NO ICES CODE)")
            self.country_input.setText("1899")
            self.cruise_number_input.setPlaceholderText(
                "if known use the format (BCDcruise_year603) else leave blank"
            )
        else:
            self.organization_input.clear()
            self.chiefscientist_input.clear()
            self.cruisedesc_input.clear()
            self.platform_input.clear()
            self.country_input.clear()
            self.cruise_number_input.clear()

    def load_last_user_metadata(self):
        if not self.meta_store_path.exists():
            self.populate_defaults("BIO")
            return

        try:
            with Path.open(self.meta_store_path, encoding="utf-8") as f:
                meta = json.load(f)

            # Populate fields safely
            input_choice = meta.get("input_choice", False)
            if input_choice:
                self.remember_input_choice = True

                processor_name = meta.get("processor_name", "")
                self.line_edit.setText(processor_name)
                self.line_edit_text = processor_name

                institution = meta.get("institution", "BIO")
                instrument = meta.get("instrument", "Minilog")
                self.institution_combo.setCurrentText(institution)
                self.instrument_combo.setCurrentText(instrument)

                default_user_meta = meta.get("default_user_meta", {})
                self.organization_input.setText(default_user_meta.get("organization", "DFO BIO"))
                self.chiefscientist_input.setText(
                    default_user_meta.get("chief_scientist", "ADAM DROZDOWSKI")
                )
                self.cruisedesc_input.setText(
                    default_user_meta.get(
                        "cruise_description", "LONG TERM TEMPERATURE MONITORING PROGRAM (LTTMP)"
                    )
                )
                self.platform_input.setText(
                    default_user_meta.get("platform_name", "BIO CRUISE DATA (NO ICES CODE)")
                )
                self.country_input.setText(default_user_meta.get("country_code", "1810"))
                self.cruise_number_input.setText(
                    default_user_meta.get(
                        "cruise_number",
                        "if known use the format (BCDcruise_year999) else leave blank",
                    )
                )

                self.remember_meta_checkbox.setChecked(self.remember_input_choice)
            else:
                self.populate_defaults("BIO")
                return

            print("✅ Loaded last user metadata")

        except Exception as e:
            print(f"⚠️ Failed to load saved metadata: {e}")


class SubWindowOne(QMainWindow):
    def __init__(self, review_mode: bool):
        super().__init__()
        self.meta_store_path = meta_dir / ".mtr_last_reviewer_metadata.json"
        self.review_mode = review_mode
        if self.review_mode:
            self.setWindowTitle("MTR QC Toolbox - ODF Quality Flagging (Review QC Mode)")
        else:
            self.setWindowTitle("MTR QC Toolbox - ODF Quality Flagging (Initial QC Mode)")
        self.resize(600, 350)

        self.line_edit_text = ""
        self.metadata_file = ""
        self.input_data_folder = ""
        self.output_data_folder = ""
        self.result = None
        self.reviewer_input_meta = {}
        self.remember_input_dict = {}
        self.remember_input_choice = False
        self.generate_batch = ""

        # --- QC Checker Name ---
        if self.review_mode:
            self.line_edit_title = QLabel("Please enter the QC reviewer name:")
        else:
            self.line_edit_title = QLabel("Please enter the QC operator name:")
        self.line_edit = QLineEdit()
        self.line_edit.setFixedHeight(28)
        font = self.line_edit.font()
        font.setPointSize(11)
        self.line_edit_title.setFont(font)
        self.line_edit.setFont(font)
        self.line_edit.editingFinished.connect(self.editing_finished)
        if self.review_mode:
            self.remember_meta_checkbox = QCheckBox("Remember last QC reviewer name")
        else:
            self.remember_meta_checkbox = QCheckBox("Remember last QC operator name")
        self.remember_meta_checkbox.setChecked(self.remember_input_choice)

        self.load_last_user_metadata()

        # --- Meta file selection ---
        self.meta_label = QLabel("Select meta data file(e.g. LFA .txt file, or Excel file):")
        self.meta_button = QPushButton("Choose Meta Data File")
        self.meta_button.setFixedSize(200, 40)
        self.meta_button.clicked.connect(self.choose_metadata_file)

        self.metadata_file_path_text = QLineEdit(" ")
        self.metadata_file_path_text.setReadOnly(True)
        self.metadata_file_path_text.setFixedWidth(500)

        # --- Input folder selection ---
        if self.review_mode:
            self.input_label = QLabel(
                "Select the Step_2_Assign_QFlag folder or other folder path containing .ODF files (With Previous Flagged):"
            )
        else:
            self.input_label = QLabel(
                "Select the Step_1_Create_ODF folder path containing .ODF files (No Previous Flagged):"
            )
        self.input_button = QPushButton("Choose ODF Folder")
        self.input_button.setFixedSize(200, 40)
        self.input_button.clicked.connect(self.choose_input_data_folder)

        self.input_path_text = QLineEdit(" ")
        self.input_path_text.setReadOnly(True)
        self.input_path_text.setFixedWidth(500)

        # --- Output folder selection ---
        self.output_label = QLabel("Select the folder path to save .ODF files:")
        self.output_button = QPushButton("Choose QC Output Folder")
        self.output_button.setFixedSize(200, 40)
        self.output_button.clicked.connect(self.choose_output_data_folder)

        self.output_path_text = QLineEdit(" ")
        self.output_path_text.setReadOnly(True)
        self.output_path_text.setFixedWidth(500)

        # --- Generated Batch Name ---
        self.generate_batch_label = QLabel("Generated batch for QC view (modify it if required):")
        self.generate_batch_text = QLineEdit(" ")
        self.generate_batch_text.setReadOnly(True)
        self.generate_batch_text.setFixedWidth(200)

        # --- OK / Cancel buttons ---
        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

        # --- LAYOUT SECTION ---
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.line_edit_title)
        title_layout.addStretch()  # push checkbox to the right
        title_layout.addWidget(self.remember_meta_checkbox)

        main_layout = QVBoxLayout()
        main_layout.addLayout(title_layout)
        main_layout.addWidget(self.line_edit)

        # Meta file row
        row0 = QHBoxLayout()
        row0.addWidget(self.meta_label)
        main_layout.addLayout(row0)

        row0b = QHBoxLayout()
        row0b.addWidget(self.meta_button)
        row0b.addWidget(self.metadata_file_path_text)
        main_layout.addLayout(row0b)

        # Input folder row
        row1 = QHBoxLayout()
        row1.addWidget(self.input_label)
        main_layout.addLayout(row1)

        row1b = QHBoxLayout()
        row1b.addWidget(self.input_button)
        row1b.addWidget(self.input_path_text)
        main_layout.addLayout(row1b)

        # Output folder row
        row2 = QHBoxLayout()
        row2.addWidget(self.output_label)
        main_layout.addLayout(row2)

        row2b = QHBoxLayout()
        row2b.addWidget(self.output_button)
        row2b.addWidget(self.output_path_text)
        main_layout.addLayout(row2b)

        # Gen batch row
        row3 = QVBoxLayout()
        row3.addWidget(self.generate_batch_label)
        row3.addWidget(self.generate_batch_text)
        main_layout.addLayout(row3)

        # Buttons centered
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.buttonBox)
        btn_row.addStretch(1)
        main_layout.addLayout(btn_row)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def editing_finished(self):
        text = self.line_edit.text().strip()
        if not text:
            return
        self.line_edit_text = text
        print("\n========== MTR Data QC Inputs ==========")
        print(f"\n(1 of 4) Data QC Reviewer: {self.line_edit_text}\n")

    def find_raw_data_folder(self, base_dir):
        """
        Search for a folder containing 'raw' in its name (case-insensitive)
        inside base_dir.
        """
        if self.review_mode is False:
            keywords = ["Step_1_Create_ODF"]
            for p in base_dir.iterdir():
                if p.is_dir() and any(keyword in p.name for keyword in keywords):
                    return p
        else:
            keywords = ["Step_2_Assign_QFlag"]
            for p in base_dir.iterdir():
                if p.is_dir() and any(keyword in p.name for keyword in keywords):
                    return p
        return None

    def build_batch_name(self, meta_path: str) -> str:
        filename = Path(Path.name(meta_path)).stem
        lfa_match = re.search(r"LFA\s*[_\-]?\s*(\d+[A-Z]?)", filename, re.IGNORECASE)

        if lfa_match:
            lfa_number = lfa_match.group(1)

            # Look for year patterns after LFA number
            year_match_4 = re.search(
                r"LFA\s*[_\-]?\s*\d+[A-Z]?[_\-]?(\d{4})", filename, re.IGNORECASE
            )
            if year_match_4:
                year_token = year_match_4.group(1)

                # 1112 → 2011_2012
                if not year_token.startswith("20"):
                    start = "20" + year_token[:2]
                    end = "20" + year_token[2:]
                    return f"LFA-{lfa_number}-{start}_{end}"

                # 2012 → keep as is
                return f"LFA-{lfa_number}-{year_token}"

            year_match_2 = re.search(
                r"LFA\s*[_\-]?\s*\d+[A-Z]?[_\-]?(\d{2})", filename, re.IGNORECASE
            )
            if year_match_2:
                year_token = year_match_2.group(1)
                return f"LFA-{lfa_number}-20{year_token}"

            # No year info
            return f"LFA-{lfa_number}"

        # ---- BCD ----
        bcd_match = re.search(r"BCD\s*[_\-]?\s*(\d+)", filename, re.IGNORECASE)
        if bcd_match:
            return f"BCD-{bcd_match.group(1)}"

        return "UNKNOWN_BATCH"

    def choose_metadata_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select the Metadata file")
        if not file_path:
            return
        if file_path:
            self.metadata_file = file_path
            self.metadata_file_path_text.setText(self.metadata_file)
            print(f"\n(2 of 4) Metadata file chosen: {file_path}\n")
            meta_path = Path(file_path)
            meta_dir = meta_path.parent
            raw_folder = self.find_raw_data_folder(meta_dir)
            if raw_folder:
                self.input_data_folder = str(raw_folder)
                self.input_path_text.setText(self.input_data_folder)

                print(f"(3 of 4) Input data folder auto-detected: {self.input_data_folder}")
            else:
                print(
                    "⚠️ No Raw data folder found near metadata file. "
                    "Please select input folder manually."
                )

            self.output_data_folder = str(meta_dir)
            self.output_path_text.setText(self.output_data_folder)
            print(f"(4 of 4) Output data folder auto-set to: {self.output_data_folder}\n")
            # extract_meta_name = os.path.basename(file_path)
            batchname = self.build_batch_name(file_path)
            self.generate_batch = batchname
            self.generate_batch_text.setText(self.generate_batch)

    def choose_input_data_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select folder with ODF files")
        if folder_path:
            self.input_data_folder = folder_path
            print(f"QC Input ODF folder selected: {folder_path}")
            self.input_path_text.setText(self.input_data_folder)

    def choose_output_data_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select QC output folder")
        if folder_path:
            self.output_data_folder = folder_path
            print(f"QC Output folder selected: {folder_path}")
            self.output_path_text.setText(self.output_data_folder)

    def on_accept(self):
        if not self.line_edit_text.strip():
            print("❌ QC reviewer name missing.")
            return

        if not self.input_data_folder:
            print("❌ ODF input folder missing.")
            return

        if not self.output_data_folder:
            print("❌ QC output folder missing.")
            return

        self.result = "accept"
        reviewer_name = self.line_edit.text().strip()
        if self.remember_meta_checkbox.isChecked():
            self.remember_input_choice = True
            self.remember_input_dict = {
                "input_choice": self.remember_input_choice,
                "reviewer_name": reviewer_name,
            }
            self.save_last_user_metadata()
        else:
            self.clear_last_user_metadata()
            self.remember_input_choice = False
            self.remember_input_dict = {}
        self.close()

    def on_reject(self):
        self.result = "reject"
        self.close()

    def save_last_user_metadata(self):
        try:
            with Path.open(self.meta_store_path, "w", encoding="utf-8") as f:
                json.dump(self.remember_input_dict, f, indent=4)
            print("💾 User metadata saved")
        except Exception as e:
            print(f"❌ Failed to save metadata: {e}")

    def clear_last_user_metadata(self):
        try:
            if self.meta_store_path.exists():
                self.meta_store_path.unlink()
                print("🗑️ Cleared saved user metadata")
        except Exception as e:
            print(f"❌ Failed to clear metadata: {e}")

    def load_last_user_metadata(self):
        if not self.meta_store_path.exists():
            self.populate_defaults()
            return

        try:
            with Path.open(self.meta_store_path, encoding="utf-8") as f:
                meta = json.load(f)
                print(meta)

            # Populate fields safely
            input_choice = meta.get("input_choice", False)
            if input_choice:
                self.remember_input_choice = True
                reviewer_name = meta.get("reviewer_name", "")
                self.line_edit.setText(reviewer_name)
                self.line_edit_text = reviewer_name
                self.remember_meta_checkbox.setChecked(self.remember_input_choice)
            else:
                self.remember_input_choice = False
                self.remember_meta_checkbox.setChecked(self.remember_input_choice)
                return

            print("✅ Loaded last user metadata")

        except Exception as e:
            print(f"⚠️ Failed to load saved metadata: {e}")

    def populate_defaults(self):
        self.line_edit.setPlaceholderText("Please Provide Reviewer Name")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # window = MainWindow()
    window = SubWindowOne(True)
    window.show()

    app.exec()
