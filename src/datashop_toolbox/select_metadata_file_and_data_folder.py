import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QFileDialog, QLabel, QLineEdit, QWidget, QDialogButtonBox
)
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.line_edit_text = ""
        self.metadata_file = ""
        self.data_folder = ""
        self.result = None  # will hold "accept" or "reject"
        self.institution = ""
        self.instrument = ""

        self.setWindowTitle("Choose Moored Thermograph Files to Process")
        self.resize(750, 380)

        self.line_edit_title = QLabel("Please enter the data processor's name in the text box below:")
        self.line_edit = QLineEdit()
        self.line_edit.setFixedHeight(25)
        font = self.line_edit_title.font()
        font.setPointSize(12)
        self.line_edit_title.setFont(font)
        self.line_edit_title.setFixedHeight(25)
        self.line_edit.setFont(font)
        self.line_edit.editingFinished.connect(self.editing_finished)

        self.institution_combo = QComboBox()
        self.institution_combo.addItems(["Unknown", "BIO", "FSRS"])
        self.institution_combo.currentTextChanged.connect( self.institution_text_changed )  # Sends the current text (string) of the selected item.

        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(["Unknown", "Minilog", "Hobo"])
        self.instrument_combo.currentTextChanged.connect( self.instrument_text_changed )  # Sends the current text (string) of the selected item.

        self.file_button = QPushButton("Select the Metadata file\n(e.g. LFA .txt file, \nor Excel file)")
        self.file_button.setFixedSize(225, 100)
        font = self.file_button.font()
        font.setPointSize(12)
        self.file_button.setFont(font)
        self.file_button.setStyleSheet("font-weight: bold;")
        self.file_button.clicked.connect(self.choose_metadata_file)

        self.folder_button = QPushButton("Select the Data folder\n(Location of *.csv files)")
        self.folder_button.setFixedSize(225, 100)
        font = self.folder_button.font()
        font.setPointSize(12)
        font.setBold(True)
        self.folder_button.setFont(font)
        self.folder_button.setStyleSheet("font-weight: bold;")
        self.folder_button.clicked.connect(self.choose_data_folder)

        self.metadata_file_label = QLabel("Metadata file selected:")
        self.metadata_file_path_text = QLineEdit(" ")
        font.setPointSize(9)
        self.metadata_file_label.setFont(font)
        self.metadata_file_label.setFixedHeight(25)
        self.metadata_file_path_text.setFont(font)
        self.metadata_file_path_text.setFixedHeight(25)

        self.data_folder_label = QLabel("Data folder selected:")
        self.data_folder_path_text = QLineEdit(" ")
        self.data_folder_label.setFont(font)
        self.data_folder_label.setFixedHeight(25)
        self.data_folder_path_text.setFont(font)
        self.data_folder_path_text.setFixedHeight(25)

        buttons = (
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

        # Vertical layout for label + line edit
        v_layout1 = QVBoxLayout()
        v_layout1.addWidget(self.line_edit_title)
        v_layout1.addWidget(self.line_edit)

        # Horizontal layout for combo boxes
        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(self.institution_combo)
        h_layout1.addWidget(self.instrument_combo)

        # Horizontal layout for buttons to open file and folder dialogs
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(self.file_button)
        h_layout2.addWidget(self.folder_button)

        # Horizontal layout for label and lineedit containing selected file
        h_layout3 = QHBoxLayout()
        h_layout3.addWidget(self.metadata_file_label)
        h_layout3.addWidget(self.metadata_file_path_text)

        # Horizontal layout for label and lineedit containing selected folder path
        h_layout4 = QHBoxLayout()
        h_layout4.addWidget(self.data_folder_label)
        h_layout4.addWidget(self.data_folder_path_text)

        v_layout2 = QVBoxLayout()
        v_layout2.addLayout(h_layout3)
        v_layout2.addLayout(h_layout4)

        # Horizontal layout for buttons used to close the window
        h_layout5 = QHBoxLayout()
        h_layout5.addStretch(1)
        h_layout5.addWidget(self.buttonBox)
        h_layout5.addStretch(1)

        # Add horizontal layouts into vertical layout
        v_layout1.addLayout(h_layout1)
        v_layout1.addLayout(h_layout2)
        v_layout1.addLayout(v_layout2)
        v_layout1.addLayout(h_layout5)

        container = QWidget()
        container.setLayout(v_layout1)
        self.setCentralWidget(container)

    def editing_finished(self):
            self.line_edit_text = self.line_edit.text()
            print(f"\n(1 of 3) Data processor: {self.line_edit_text}\n")

    def institution_text_changed(self, s):
        self.institution = s

    def instrument_text_changed(self, s):
        self.instrument = s

    def choose_metadata_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select the Metadata file")
        if file_path:
            self.metadata_file = file_path
            print(f"\n(2 of 3) Metadata file chosen: {file_path}\n")
            self.metadata_file_path_text.setText(self.metadata_file)

    def choose_data_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select the Data folder")
        if folder_path:
            self.data_folder = folder_path
            print(f"\n(3 of 3) Data file folder selected: {folder_path}\n")
            self.data_folder_path_text.setText(self.data_folder)

    def on_accept(self):
        self.result = "accept"
        self.close()

    def on_reject(self):
        self.result = "reject"
        self.close()


if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    app.exec()
