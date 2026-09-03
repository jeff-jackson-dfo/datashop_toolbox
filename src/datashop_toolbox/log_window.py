# log_window.py
import logging
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogEmitter(QObject):
    """Qt object that emits a signal carrying a line of log text.

    Attributes:
        text_written: Signal emitted with a line of text to append to
            a log display.
    """

    text_written = Signal(str)


class LogWindow(QWidget):
    """Standalone window that displays streamed log/print output.

    Provides a read-only text area that log lines can be appended to
    from any thread (via :attr:`emitter`), plus buttons to export the
    log to a text file or request that the host application exit.

    Attributes:
        exit_requested: Signal emitted when the user clicks the "Exit
            Program" button.
        active_workers: List of active :class:`Worker` threads kept
            alive by callers to prevent premature garbage collection.
        log_box: Read-only text widget displaying the log.
        emitter: :class:`LogEmitter` used to append text to
            :attr:`log_box` from any thread.
        export_button: Button that exports the log to a text file.
    """

    exit_requested = Signal()

    def __init__(self, parent=None):
        """Build the log window's widgets and layout.

        Args:
            parent: Optional parent widget.
        """
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
        self._bring_to_front_and_maximize()

    def _append_text(self, text: str):
        """Append a line of text to the log box and scroll to it.

        Args:
            text: Line of text to append.
        """
        # append text and auto-scroll
        self.log_box.append(text)
        self.log_box.ensureCursorVisible()

    def write(self, text: str):
        """Directly append text (convenience).

        Args:
            text: Text to append. Ignored if empty or whitespace-only.
        """
        if text and text.strip():
            self.emitter.text_written.emit(text)

    def redirect_prints_to_log(self):
        """Call this to redirect sys.stdout to the log window (optional)."""

        class _Stream:
            """File-like object that forwards writes to a :class:`LogEmitter`."""

            def __init__(self, emitter):
                """Initialize the stream.

                Args:
                    emitter: :class:`LogEmitter` to forward writes to.
                """
                self.emitter = emitter

            def write(self, msg):
                """Forward a non-blank message to the emitter.

                Args:
                    msg: Text to forward.
                """
                if msg and msg.strip():
                    self.emitter.text_written.emit(msg)

            def flush(self):
                """No-op flush, present for file-like compatibility."""
                pass

        sys.stdout = _Stream(self.emitter)
        sys.stderr = _Stream(self.emitter)
        self.write(
            "************* ❌ The log window should not be closed during processing ❌ ***************"
        )

    def export_log(self):
        """Export the current log content to a text file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "", "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with Path.open(filename, "w", encoding="utf-8") as f:
                    f.write(self.log_box.toPlainText())
                self._append_text(f"\n✅ Log exported to: {filename}")
            except Exception as e:
                self._append_text(f"\n❌ Failed to export log: {e}")

    def _exit_app(self):
        """Emit exit request to Main Application."""
        self.exit_requested.emit()

    def _bring_to_front_and_maximize(self):
            """
            Brings the window to the front and maximizes it.
            """
            # Show the window if hidden
            if not self.isVisible():
                self.show()

            # Maximize the window
            self.showMaximized()

            # Bring to front and focus
            self.raise_()
            self.activateWindow()

            # On some OSes, you may need to force focus
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)

class Worker(QThread):
    """Background thread that runs a callable and reports its outcome.

    Attributes:
        log: Signal emitted with a line of log text produced by the
            running function.
        finished_success: Signal emitted when the function completes
            without raising.
        finished_failure: Signal emitted with an error message if the
            function raises.
    """

    log = Signal(str)
    finished_success = Signal()
    finished_failure = Signal(str)

    def __init__(self, func, *args, **kwargs):
        """Initialize the worker.

        Args:
            func: Callable to run on the background thread. Called as
                ``func(self.log.emit, *args, **kwargs)``, so it should
                accept a log-callback as its first argument.
            *args: Additional positional arguments passed to ``func``.
            **kwargs: Additional keyword arguments passed to ``func``.
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Run ``func`` on this thread and emit the resulting signal.

        Emits :attr:`finished_success` if ``func`` completes normally,
        or :attr:`finished_failure` (after logging the exception and
        traceback via :attr:`log`) if it raises.
        """
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
        """Strip characters that cp1252 cannot encode from a log record.

        Args:
            record: Log record whose ``msg`` attribute is checked and,
                if necessary, sanitized in place.

        Returns:
            ``True`` always, so the record is never filtered out.
        """
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
        """Initialize the handler.

        Args:
            text_edit: Widget that formatted log records are appended
                to. The handler's level is set to ``INFO``.
        """
        super().__init__()
        self.text_edit = text_edit
        self.setLevel(logging.INFO)
        self.setFormatter(logging.Formatter("%(asctime)s — %(levelname)s — %(message)s"))

    def emit(self, record):
        """Format a log record and append it to the text widget.

        Args:
            record: Log record to format and display. Any exception
                raised while formatting or appending is silently
                ignored.
        """
        try:
            msg = self.format(record)
            # append text to QTextEdit safely
            self.text_edit.append(msg)
        except Exception:
            pass


class LogWindowThermographQC(QWidget):
    """Log window for the interactive thermograph QC workflow.

    Attributes:
        log_view: Read-only text widget displaying the log.
        radio_opt: Toggle for enabling QC-reviewer mode.
        btn_start: Button that starts the thermograph visual QC
            process.
        btn_exit: Button that exits the program.
        qtext_handler: :class:`QTextEditLogger` attached to
            :attr:`log_view`.
    """

    def __init__(self):
        """Build the window's widgets and layout."""
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
    """Log window for processing raw MTR (thermograph) files to ODF.

    Attributes:
        log_view: Read-only text widget displaying the log.
        btn_start: Button that starts processing of raw ``.csv`` MTR
            files.
        btn_exit: Button that exits the program.
        qtext_handler: :class:`QTextEditLogger` attached to
            :attr:`log_view`.
    """

    def __init__(self):
        """Build the window's widgets and layout."""
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


class LogWindowCTDQC(QWidget):
    """Log window for the interactive CTD QC workflow.

    Attributes:
        log_view: Read-only text widget displaying the log.
        radio_opt: Toggle for enabling QC-reviewer mode.
        btn_start: Button that starts the CTD visual QC process.
        btn_exit: Button that exits the program.
        qtext_handler: :class:`QTextEditLogger` attached to
            :attr:`log_view`.
    """

    def __init__(self):
        """Build the window's widgets and layout."""
        super().__init__()
        self.setWindowTitle("CTD QC — Log Window")
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        # Log display
        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.radio_opt = QRadioButton("Enable As QC Reviewer Mode")
        layout.addWidget(self.radio_opt)

        # Buttons
        self.btn_start = QPushButton("Start Visual QC Process for CTD Data (ODF Files)")
        self.btn_exit = QPushButton("Exit Program")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_exit)
        self.qtext_handler = QTextEditLogger(self.log_view)


class LogWindowProcessCTD(QWidget):
    """Log window for the CTD ODF-file processing/inspection workflow.

    Attributes:
        log_view: Read-only text widget displaying the log.
        btn_start: Button that starts visual inspection of CTD ODF
            files.
        btn_exit: Button that exits the program.
        qtext_handler: :class:`QTextEditLogger` attached to
            :attr:`log_view`.
    """

    def __init__(self):
        """Build the window's widgets and layout."""
        super().__init__()
        self.setWindowTitle("CTD Processing — Log Window")
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        # Log display
        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # Buttons
        self.btn_start = QPushButton("Start Visual Inspection of CTD ODF Files")
        self.btn_exit = QPushButton("Exit Program")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_exit)
        self.qtext_handler = QTextEditLogger(self.log_view)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LogWindow()
    window.show()
    # window.redirect_prints_to_log()

    print("✅ Log window initialized successfully.")

    sys.exit(app.exec())
