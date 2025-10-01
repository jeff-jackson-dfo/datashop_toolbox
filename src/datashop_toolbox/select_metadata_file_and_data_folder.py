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

        self.setWindowTitle("Choose Moored Thermograph Files to Process")
        self.resize(525, 350)

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
        self.institution_combo.addItems(["BIO", "FSRS"])        
        # self.institution_combo.currentIndexChanged.connect( self.institution_index_changed ) # Sends the current index (position) of the selected item.
        self.institution_combo.currentTextChanged.connect( self.institution_text_changed )  # Sends the current text (string) of the selected item.

        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(["Minilog", "Hobo"])
        # self.instrument_combo.currentIndexChanged.connect( self.instrument_index_changed ) # Sends the current index (position) of the selected item.
        self.instrument_combo.currentTextChanged.connect( self.instrument_text_changed )  # Sends the current text (string) of the selected item.

        self.file_button = QPushButton("Select the Metadata file\n(e.g. LFA .txt file, \nor Excel file)")
        self.file_button.setFixedSize(225, 100)
        font = self.file_button.font()
        font.setPointSize(12)
        # font.setBold(True)
        self.file_button.setFont(font)
        # self.file_button.setStyleSheet("color: blue; font-weight: bold;")
        self.file_button.setStyleSheet("font-weight: bold;")
        # icon = QStyle.standardIcon(QStyle.SP_FileIcon)
        # self.file_button.setIcon(icon)
        self.file_button.clicked.connect(self.choose_metadata_file)

        self.folder_button = QPushButton("Select the Data folder\n(Location of *.csv files)")
        self.folder_button.setFixedSize(225, 100)
        font = self.folder_button.font()
        font.setPointSize(12)
        font.setBold(True)
        self.folder_button.setFont(font)
        # self.folder_button.setStyleSheet("color: blue; font-weight: bold;")
        self.folder_button.setStyleSheet("font-weight: bold;")
        self.folder_button.clicked.connect(self.choose_data_folder)

        buttons = (
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

        # self.ok_button = QPushButton("OK")
        # self.ok_button.setFixedSize(80, 40)
        # self.ok_button.setStyleSheet("font-weight: bold;")
        # self.cancel_button = QPushButton("Cancel")
        # self.cancel_button.setFixedSize(80, 40)
        # self.cancel_button.setStyleSheet("font-weight: bold;")

        # Vertical layout for label + line edit
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.line_edit_title)
        v_layout.addWidget(self.line_edit)

        # Horizontal layout for combo boxes
        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(self.institution_combo)
        h_layout1.addWidget(self.instrument_combo)

        # Horizontal layout for buttons to open file and folder dialogs
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(self.file_button)
        h_layout2.addWidget(self.folder_button)

        # Horizontal layout for buttons used to close the window
        h_layout3 = QHBoxLayout()
        h_layout3.addStretch(1)
        h_layout3.addWidget(self.buttonBox)
        h_layout3.addStretch(1)

        # Add horizontal layouts into vertical layout
        v_layout.addLayout(h_layout1)
        v_layout.addLayout(h_layout2)
        v_layout.addLayout(h_layout3)

        container = QWidget()
        container.setLayout(v_layout)
        self.setCentralWidget(container)

    def editing_finished(self):
            self.line_edit_text = self.line_edit.text()
            print(f"\n(1 of 3) Data processor: {self.line_edit_text}\n")

    # def institution_index_changed(self, i): # i is an int
    #     print(i)

    def institution_text_changed(self, s): # s is a str
        print(s)

    # def instrument_index_changed(self, i): # i is an int
    #     print(i)

    def instrument_text_changed(self, s): # s is a str
        print(s)

    def choose_metadata_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select the Metadata file")
        if file_path:
            self.metadata_file = file_path
            print(f"\n(2 of 3) Metadata file chosen: {file_path}\n")

    def choose_data_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select the Data folder")
        if folder_path:
            self.data_folder = folder_path
            print(f"\n(3 of 3) Data file folder selected: {folder_path}\n")

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
