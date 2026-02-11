# log_window.py
from PySide6.QtWidgets import (
    QApplication,
    QWidget, 
    QVBoxLayout, 
    QTextEdit, 
    QPushButton, 
    QFileDialog, 
    QHBoxLayout,
    QRadioButton)
from PySide6.QtCore import Signal, QObject, QThread
import sys
import traceback
import logging


class LogEmitter(QObject):
    text_written = Signal(str)

class LogWindow(QWidget):
    exit_requested = Signal()
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
    log = Signal(str)
    finished_success = Signal()
    finished_failure = Signal(str)

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

class SafeConsoleFilter(logging.Filter):
    """Ensures console output is cp1252-safe by stripping unsupported characters."""
    def filter(self, record):
        try:
            # Attempt cp1252 encoding (Windows terminal)
            record.msg.encode("cp1252")
        except UnicodeEncodeError:
            # Remove or replace unsupported characters (emoji, symbols)
            record.msg = record.msg.encode("ascii", "ignore").decode()
        return True

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

class SafeConsoleFilter(logging.Filter):
    """Remove unsupported characters (like emojis) for console output."""
    def filter(self, record):
        try:
            record.msg.encode("cp1252")
        except UnicodeEncodeError:
            # replace emoji with a safe fallback
            record.msg = record.msg.encode("ascii", "ignore").decode()
        return True

class LogWindowThermographQC(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermograph QC — Log Window")
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        # Log display
        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.radio_opt = QRadioButton("Enable As QC Reviewer Mode")
        layout.addWidget(self.radio_opt)

        # Buttons
        self.btn_start = QPushButton("Start Visual QC Process for Thermograph Data (ODF Files)")
        self.btn_exit = QPushButton("Exit Program")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_exit)
        self.qtext_handler = QTextEditLogger(self.log_view)
        
class LogWindowProcessMTR(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermograph Processing — Log Window")
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        # Log display
        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # Buttons
        self.btn_start = QPushButton("Start Processing of Raw (.csv) MTR Files (to ODF Format)")
        self.btn_exit = QPushButton("Exit Program")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_exit)
        self.qtext_handler = QTextEditLogger(self.log_view)

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = LogWindowUI()
    window.show()
    #window.redirect_prints_to_log()

    print("✅ Log window initialized successfully.")

    sys.exit(app.exec())