
import sys

from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

# Use the generated Python from Qt Designer instead of loading the .ui at runtime
from .ui_thermograph_main_window import Ui_thermograph_main_window


class ThermographMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Set up the UI from the generated module
        self.ui = Ui_thermograph_main_window()
        self.ui.setupUi(self)

        # Internal state
        self.metadata_file = ""
        self.data_folder = ""
        self.processor_name = ""
        self.institution = ""
        self.instrument = ""
        self.result = None

        # Connect signals to slots using the widget object names as generated
        self.ui.name_line_edit.editingFinished.connect(self.on_name_entered)
        self.ui.institution_combo_box.currentTextChanged.connect(self.on_institution_changed)
        self.ui.instrument_combo_box.currentTextChanged.connect(self.on_instrument_changed)
        self.ui.metadata_push_button.clicked.connect(self.choose_metadata_file)
        self.ui.data_folder_push_button.clicked.connect(self.choose_data_folder)
        self.ui.dialog_button_box.accepted.connect(self.accept_clicked)
        self.ui.dialog_button_box.rejected.connect(self.reject_clicked)

    # --- Slots ---
    def on_name_entered(self):
        self.processor_name = self.ui.name_line_edit.text()
        print(f"(1 of 3) Data processor: {self.processor_name}")

    def on_institution_changed(self, text: str):
        self.institution = text

    def on_instrument_changed(self, text: str):
        self.instrument = text

    def choose_metadata_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select the Metadata file")
        if file_path:
            self.metadata_file = file_path
            self.ui.metadata_line_edit.setText(file_path)
            print(f"(2 of 3) Metadata file: {file_path}")

    def choose_data_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select the Data folder")
        if folder_path:
            self.data_folder = folder_path
            self.ui.data_folder_line_edit.setText(folder_path)
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
