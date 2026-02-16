import sys

from PySide6 import uic
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow


class ThermographMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("thermograph_gui.ui", self)  # Load the .ui file

        # Connect signals
        self.lineEdit_name.editingFinished.connect(self.on_name_entered)
        self.combo_institution.currentTextChanged.connect(self.on_institution_changed)
        self.combo_instrument.currentTextChanged.connect(self.on_instrument_changed)
        self.button_metadata.clicked.connect(self.choose_metadata_file)
        self.button_datafolder.clicked.connect(self.choose_data_folder)
        self.buttonBox.accepted.connect(self.accept_clicked)
        self.buttonBox.rejected.connect(self.reject_clicked)

        # Internal state
        self.metadata_file = ""
        self.data_folder = ""
        self.processor_name = ""
        self.institution = ""
        self.instrument = ""
        self.result = None

    def on_name_entered(self):
        self.processor_name = self.lineEdit_name.text()
        print(f"(1 of 3) Data processor: {self.processor_name}")

    def on_institution_changed(self, text):
        self.institution = text

    def on_instrument_changed(self, text):
        self.instrument = text

    def choose_metadata_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select the Metadata file")
        if file_path:
            self.metadata_file = file_path
            self.lineEdit_metadata.setText(file_path)
            print(f"(2 of 3) Metadata file: {file_path}")

    def choose_data_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select the Data folder")
        if folder_path:
            self.data_folder = folder_path
            self.lineEdit_datafolder.setText(folder_path)
            print(f"(3 of 3) Data folder: {folder_path}")

    def accept_clicked(self):
        self.result = "accept"
        self.close()

    def reject_clicked(self):
        self.result = "reject"
        self.close()


def main():
    app = QApplication(sys.argv)
    window = ThermographMainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
