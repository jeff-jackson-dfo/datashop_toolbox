import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QFileDialog, QLabel, QLineEdit, QWidget, QDialogButtonBox
)
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()

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
        
        # --- Data Processor Name ---
        self.line_edit_title = QLabel("Please enter the data processor's name in the text box below:")
        self.line_edit = QLineEdit()
        self.line_edit.setFixedHeight(25)
        font = self.line_edit_title.font()
        font.setPointSize(12)
        self.line_edit_title.setFont(font)
        self.line_edit_title.setFixedHeight(25)
        self.line_edit.setFont(font)
        self.line_edit.editingFinished.connect(self.editing_finished)

        # --- Institution Combo ---
        self.institution_combo_label = QLabel("Select institution:")
        self.institution_combo_label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        self.institution_combo_label.setFixedSize(225, 15)
        self.institution_combo = QComboBox()
        self.institution_combo.addItems(["BIO", "FSRS"])
        self.institution_combo.currentTextChanged.connect(self.institution_text_changed)  # Sends the current text (string) of the selected item.
        self.institution_combo.setCurrentIndex(0)

        # --- Instrument Combo ---
        self.instrument_combo_label = QLabel("Select instrument:")
        self.instrument_combo_label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        self.instrument_combo_label.setFixedSize(225, 15)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(["Minilog", "Hobo"])
        self.instrument_combo.currentTextChanged.connect( self.instrument_text_changed )  # Sends the current text (string) of the selected item.
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

        # Default values for "BIO"
        self.populate_defaults("BIO")

        # --- Buttons for Metadata + Data Folder ---
        self.file_button = QPushButton("Select meta data file\n(e.g. LFA .txt file, \nor Excel file)")
        self.file_button.setFixedSize(225, 100)
        font = self.file_button.font()
        font.setPointSize(11)
        font.setBold(True)
        self.file_button.setFont(font)
        self.file_button.setStyleSheet("font-weight: bold;")
        self.file_button.clicked.connect(self.choose_metadata_file)

        self.input_data_folder_button = QPushButton("Select input data folder\n(Location of raw *.csv files)")
        self.input_data_folder_button.setFixedSize(225, 100)
        font = self.input_data_folder_button.font()
        font.setPointSize(11)
        font.setBold(True)
        self.input_data_folder_button.setFont(font)
        self.input_data_folder_button.setStyleSheet("font-weight: bold;")
        self.input_data_folder_button.clicked.connect(self.choose_input_data_folder)

        self.output_data_folder_button = QPushButton("Select output data folder\n(Location for *.odf files)")
        self.output_data_folder_button.setFixedSize(225, 100)
        font = self.output_data_folder_button.font()
        font.setPointSize(11)
        font.setBold(True)
        self.output_data_folder_button.setFont(font)
        self.output_data_folder_button.setStyleSheet("font-weight: bold;")
        self.output_data_folder_button.clicked.connect(self.choose_output_data_folder)

         # --- Dialog Buttons ---
        buttons = (
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
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
     
        # Vertical layout for label + line edit
        v_layout1 = QVBoxLayout()
        v_layout1.addWidget(self.line_edit_title)
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
            self.line_edit_text = self.line_edit.text()
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
            self.instrument = "Minilog"   # ensure consistency
        # Update cruise header defaults
        self.populate_defaults(s)

    def instrument_text_changed(self, s):
        self.instrument = s

    def choose_metadata_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select the Metadata file")
        if file_path:
            self.metadata_file = file_path
            print(f"\n(2 of 4) Metadata file chosen: {file_path}\n")
            self.metadata_file_path_text.setText(self.metadata_file)

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

        #self.close()
        self.hide()

    def on_reject(self):
        self.result = "reject"
        self.close()

    def populate_defaults(self, institution):
        """Populate 4 fields based on institution selection."""
        if institution == "BIO":
            self.organization_input.setText("DFO BIO")
            self.chiefscientist_input.setText("ADAM DROZDOWSKI")
            self.cruisedesc_input.setText("LONG TERM TEMPERATURE MONITORING PROGRAM (LTTMP)")
            self.platform_input.setText("BIO CRUISE DATA (NO ICES CODE)")
            self.country_input.setText("1810")
            self.cruise_number_input.setPlaceholderText("if known use the format (BCDcruise_year999) else leave blank ")
        elif institution == "FSRS":
            self.organization_input.setText("FSRS")
            self.chiefscientist_input.setText("SHANNON SCOTT-TIBBETTS")
            self.cruisedesc_input.setText("FISHERMEN  AND SCIENTISTS RESEARCH SOCIETY")
            self.platform_input.setText("FSRS CRUISE DATA (NO ICES CODE)")
            self.country_input.setText("1899")
            self.cruise_number_input.setPlaceholderText("if known use the format (BCDcruise_year603) else leave blank ")
        else:
            self.organization_input.clear()
            self.chiefscientist_input.clear()
            self.cruisedesc_input.clear()
            self.platform_input.clear()
            self.country_input.clear()
            self.cruise_number_input.clear()

class SubWindowOne(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("MTR QC Toolbox - ODF Quality Flagging ")
        self.resize(600, 350)

        self.qc_name = ""
        self.input_data_folder = ""
        self.output_data_folder = ""
        self.result = None

        # --- QC Checker Name ---
        self.line_edit_title = QLabel("Please enter the QC reviewer name:")
        self.line_edit = QLineEdit()
        self.line_edit.setFixedHeight(28)
        font = self.line_edit.font()
        font.setPointSize(11)
        self.line_edit_title.setFont(font)
        self.line_edit.setFont(font)
        self.line_edit.editingFinished.connect(self.editing_finished)

        # --- Input folder selection ---
        self.input_label = QLabel("Select the folder path containing .ODF files:")
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

        # --- OK / Cancel buttons ---
        buttons = (
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

        # --- LAYOUT SECTION ---
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.line_edit_title)
        main_layout.addWidget(self.line_edit)

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
        self.qc_name = self.line_edit.text().strip()
        print(f"QC Reviewer: {self.qc_name}")

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
        if not self.qc_name.strip():
            print("❌ QC reviewer name missing.")
            return
        
        if not self.input_data_folder:
            print("❌ ODF input folder missing.")
            return

        if not self.output_data_folder:
            print("❌ QC output folder missing.")
            return

        self.result = "accept"
        self.close()

    def on_reject(self):
        self.result = "reject"
        self.close()


if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    #window = MainWindow()
    window = SubWindowOne()
    window.show()

    app.exec()
