# log_window.py
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QFileDialog, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, QObject, QThread, Qt
import sys
import traceback
import logging

from PyQt6.QtCore import Qt

class LogEmitter(QObject):
    text_written = pyqtSignal(str)

class LogWindow(QWidget):
    exit_requested = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Log")
        self.resize(800, 420)
        self.active_workers = [] 
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setAcceptRichText(False)

        exit_btn = QPushButton("Exit Program")
        exit_btn.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
        exit_btn.clicked.connect(self._exit_app)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(exit_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.log_box)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.emitter = LogEmitter()
        self.emitter.text_written.connect(self._append_text)

        self.export_button = QPushButton("Export Log")
        self.export_button.clicked.connect(self.export_log)
        self.layout().addWidget(self.export_button)

    def _append_text(self, text: str):
        # append text and auto-scroll
        self.log_box.append(text)
        self.log_box.ensureCursorVisible()

    def write(self, text: str):
        """Directly append text (convenience)."""
        if text and text.strip():
            self.emitter.text_written.emit(text)

    def redirect_prints_to_log(self):
        """Call this to redirect sys.stdout to the log window (optional)."""
        class _Stream:
            def __init__(self, emitter):
                self.emitter = emitter
            def write(self, msg):
                if msg and msg.strip():
                    self.emitter.text_written.emit(msg)
            def flush(self):
                pass
        sys.stdout = _Stream(self.emitter)
        sys.stderr = _Stream(self.emitter)
        self.write("************* ❌ The log window should not be closed during processing ❌ ***************")

    def export_log(self):
        """Export the current log content to a text file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "", "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.log_box.toPlainText())
                self._append_text(f"\n✅ Log exported to: {filename}")
            except Exception as e:
                self._append_text(f"\n❌ Failed to export log: {e}")

    def _exit_app(self):
        """Emit exit request to Main Application."""
        self.exit_requested.emit()

class Worker(QThread):
    log = pyqtSignal(str)
    finished_success = pyqtSignal()
    finished_failure = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # Run long function, send log callback
            self.func(self.log.emit, *self.args, **self.kwargs)
            self.finished_success.emit()
        except Exception as e:
            tb = traceback.format_exc()
            self.log.emit("❌ ERROR: " + str(e))
            self.log.emit(tb)
            self.finished_failure.emit(str(e))

class LogWindowUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermograph QC Log Window")
        self.resize(700, 600)

        layout = QVBoxLayout(self)

        # log view
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # buttons
        self.btn_start = QPushButton("Start QC")
        self.btn_show_log = QPushButton("Open Log File")
        self.btn_reload = QPushButton("Load Main Again")
        self.btn_exit = QPushButton("Exit Program")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_show_log)
        layout.addWidget(self.btn_reload)
        layout.addWidget(self.btn_exit)

    def append_log(self, text):
        self.log_view.append(text)

class QTextEditLogger(logging.Handler):
    """A logging.Handler that appends logs to a QTextEdit widget in the GUI."""

    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.text_edit = text_edit
        self.setLevel(logging.INFO)
        self.setFormatter(logging.Formatter("%(asctime)s — %(levelname)s — %(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            # append text to QTextEdit safely
            self.text_edit.append(msg)
        except Exception:
            pass

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = LogWindow()
    window.show()
    #window.redirect_prints_to_log()

    print("✅ Log window initialized successfully.")

    sys.exit(app.exec())