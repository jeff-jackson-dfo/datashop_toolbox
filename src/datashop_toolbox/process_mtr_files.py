import logging
import os
import posixpath
import queue
import re
import sys
import time
import traceback
from datetime import datetime
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QInputDialog

from datashop_toolbox import select_metadata_file_and_data_folder
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.log_window import LogWindow, LogWindowProcessMTR, Worker
from datashop_toolbox.qualityhdr import QualityHeader
from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.validated_base import get_current_date_time


## main_automated_start_qc
def process_mtr_files_for_worker(
    log,
    metadata_file_path,
    input_data_folder_path,
    output_data_folder_path,
    operator,
    institution,
    instrument,
    batch_id,
    user_input_metadata,
):
    # -------------------------------------------------------------
    #  """Process MTR files to generate ODF files."""
    # -------------------------------------------------------------
    start_time = datetime.now()
    log(f"✅ Batch start : {batch_id} ✅ ")
    log(f"MTR Data Processing Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log(f"Data processor: {operator}")
    log(f"Institution: {institution}")
    log(f"Instrument: {instrument}")
    log(f"User metadata: {user_input_metadata}\n")
    log(f"Metadata file: {metadata_file_path}")
    log(f"Input data folder path: {input_data_folder_path}")
    log(f"Output data folder path: {output_data_folder_path}")

    # Change directory
    try:
        os.chdir(input_data_folder_path)
        log(f"Changed working dir to the input directory: {input_data_folder_path}")
    except Exception as e:
        raise RuntimeError(f"Cannot change directory: {e}")

    # Look for CSV files
    all_files = Path.glob("*.csv")
    if not all_files:
        log(f"No CSV files found in: {input_data_folder_path}")
        return

    # Prepare output folder
    odf_path = Path(output_data_folder_path / "Step_1_Create_ODF")
    Path.makedir(odf_path, parent=True)
    log(f"Created a output data folder name: Step_1_Create_ODF and path for .odf files: {odf_path}")

    # Loop through the CSV files to generate an ODF file for each.
    # for file_name in all_files:
    for idx, file_name in enumerate(all_files, start=1):
        log("")
        log("#######################################################################")
        log(f"=== Start processing MTR file {idx} of {len(all_files)}: {file_name} ===")
        log("#######################################################################")
        log("")

        mtr_path = posixpath.join(input_data_folder_path, file_name)
        log(f"\nProcessing MTR raw file: {mtr_path}\n")

        try:
            mtr = ThermographHeader()

            history_header = HistoryHeader()
            history_header.creation_date = get_current_date_time()
            history_header.set_process(f"INITIAL FILE CREATED BY {operator.upper()}")
            mtr.history_headers.append(history_header)

            mtr.process_thermograph(
                institution, instrument, metadata_file_path, mtr_path, user_input_metadata
            )

            file_spec = mtr.generate_file_spec()
            mtr.file_specification = file_spec
            mtr.add_quality_flags()

            quality_header = QualityHeader()
            quality_header.quality_date = get_current_date_time()
            quality_header.add_quality_codes()
            mtr.quality_header = quality_header

            mtr.update_odf()

            odf_file_path = posixpath.join(odf_path, file_spec + ".ODF")
            log(f"Writing ODF file [{idx}/{len(all_files)}]: {odf_file_path}")
            mtr.write_odf(odf_file_path, version=2.0)
            log(f"SUCCESS: {file_name} → {odf_file_path}")

            # Reset the shared log list
            BaseHeader.reset_log_list()
        except Exception as e:
            log(f"ERROR processing {file_name}: {e}")
            log(traceback.format_exc())
        log("")
        log("#######################################################################")
        log(f"=== End processing MTR file {idx} of {len(all_files)}: {file_name} ===")
        log("#######################################################################")
        log("")

    if idx == len(all_files):
        end_time = datetime.now()
        duration = end_time - start_time
        log(
            f"[{idx}/{len(all_files)}] MTR Data Processing Completed at: \
            {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        log(f"Total Processing Time: {str(duration)}")
        log(f"✅ [{idx}/{len(all_files)}] Batch end : {batch_id} ✅ \n")


def main_automated_start_qc():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Create log window first
    log_window = LogWindow()
    log_window.show()
    log_window.redirect_prints_to_log()
    print(
        "\n"
        "========================================\n"
        " MTR DATA PROCESSING — INPUT REQUIRED\n"
        "========================================\n"
        "\n"
        "Please provide all required inputs before starting:\n"
        "\n"
        "STEP 1 of 6  ➜ Enter data processor name\n"
        "STEP 2 of 6  ➜ Choose the correct institution (e.g., DFO BIO, FSRS)\n"
        "STEP 3 of 6  ➜ Select the appropriate instrument type\n"
        "STEP 4 of 6  ➜ Select metadata file\n"
        "STEP 5 of 6  ➜ Select input data folder\n"
        "STEP 6 of 6  ➜ Select output data folder\n"
        "\n"
        "ADDITIONAL SETTINGS:\n"
        " • Use default user meta data if not provide appropiate user metadata\n"
        "\n"
        "NEXT:\n"
        " • Click 'Start' to begin processing\n"
        " • Select one batch at a time. After finish start new batch\n"
        "\n"
        "STATUS:\n"
        " • Monitor progress in the terminal\n"
        "\n"
        "========================================"
    )
    log_window.active_workers = []
    selector_holder = {"select_inputs": None}

    def exit_everything():
        log_window.write("⚠️ Exiting program...")
        # Stop all active workers
        for w in list(log_window.active_workers):
            try:
                if w.isRunning():
                    w.requestInterruption()
                    w.quit()
                    w.wait()
            except Exception:
                pass
        log_window.active_workers.clear()
        sel = selector_holder.get("select_inputs")
        if sel is not None:
            try:
                sel.close()
            except Exception:
                pass
            selector_holder["select_inputs"] = None
        try:
            log_window.close()
        except Exception:
            pass

        QApplication.quit()
        sys.exit(0)

    log_window.exit_requested.connect(exit_everything)

    def start_selection():
        select_inputs = select_metadata_file_and_data_folder.MainWindow()
        selector_holder["select_inputs"] = select_inputs
        select_inputs.show()
        if not log_window.isVisible():
            log_window.show()

        def on_accept():
            # Read values from UI
            metadata_file_path = select_inputs.metadata_file
            input_data_folder_path = select_inputs.input_data_folder
            output_data_folder_path = select_inputs.output_data_folder
            operator = select_inputs.line_edit_text.strip()
            institution = select_inputs.institution.upper()
            instrument = select_inputs.instrument.lower()
            user_input_metadata = select_inputs.user_input_meta

            if not operator:
                operator, ok = QInputDialog.getText(
                    select_inputs,
                    "Data processor Name Required",
                    "Please enter the name of the analyst performing the data processing:",
                )
                if not ok or not operator.strip():
                    log_window.write("❌ Operator name is required. Batch cancelled.")
                    return

            if not metadata_file_path or not input_data_folder_path or not output_data_folder_path:
                log_window.write(
                    "❌ Missing metadata or input/output folder. Improper selections made. Please try again. or exiting program....."
                )
                return

            if institution == "BIO":
                match = re.search(r"BCD\d+999", metadata_file_path, re.IGNORECASE)
                if match:
                    cruise_number = match.group(0)
                elif "_" in metadata_file_path:
                    cruise_number = metadata_file_path.split("_")[1].split(".")[0]
                else:
                    cruise_number = metadata_file_path

                batch_id = f"MTR_{cruise_number}_{instrument}_{institution}"

            elif institution == "FSRS":
                pattern = r"\b(LFA)\b\s+(\d+_\d+)"
                match = re.search(pattern, metadata_file_path, re.IGNORECASE)
                if match:
                    cruise_number = match.group(1).upper() + "-" + match.group(2).replace("_", "")
                else:
                    cruise_number = metadata_file_path
                batch_id = f"MTR_{cruise_number}_{instrument}_{institution}"

            else:
                batch_id = f"MTR_{Path.name(metadata_file_path).split('.')[0]}_{instrument}_{institution}"

            # Start worker thread
            worker = Worker(
                process_mtr_files_for_worker,
                metadata_file_path,
                input_data_folder_path,
                output_data_folder_path,
                operator,
                institution,
                instrument,
                batch_id,
                user_input_metadata,
            )

            log_window.active_workers.append(worker)
            worker.log.connect(log_window.write)

            def on_success():
                log_window.write(
                    "\n✅ ✅ ✅ <<< Batch completed successfully. Please select next batch to continue >>> ✅ ✅ ✅ \n"
                )
                if worker in log_window.active_workers:
                    log_window.active_workers.remove(worker)
                worker.deleteLater()
                start_selection()  # open next batch window

            def on_failure(msg):
                log_window.write(f"\n❌ Batch FAILED:\n{msg}\n")
                if worker in log_window.active_workers:
                    log_window.active_workers.remove(worker)
                worker.deleteLater()
                start_selection()  # allow next batch

            worker.start()
            select_inputs.hide()

            worker.finished_success.connect(on_success)
            worker.finished_failure.connect(on_failure)

        def on_reject():
            log_window.write("\nOperation cancelled by user. Exiting…")
            selector_holder["select_inputs"] = None
            select_inputs.close()
            app.quit()

        select_inputs.buttonBox.accepted.connect(on_accept)
        select_inputs.buttonBox.rejected.connect(on_reject)

    # Start the first batch selection
    QTimer.singleShot(0, start_selection)
    print("===============================================\n")

    sys.exit(app.exec())


## main_manual_start_qc


class MTRProcessingThread(QThread):
    """
    Worker thread to process MTR data without blocking the GUI.
    """

    finished = Signal(bool)  # Signal to indicate processing done

    def __init__(
        self,
        metadata_file_path,
        input_path,
        output_path,
        operator,
        institution,
        instrument,
        user_metadata,
        batch_id,
    ):
        super().__init__()
        self.metadata_file_path = metadata_file_path
        self.input_path = input_path
        self.output_path = output_path
        self.operator = operator
        self.institution = institution
        self.instrument = instrument
        self.user_metadata = user_metadata
        self.batch_id = batch_id

    def run(self):
        try:
            task_result = run_process_thermograph_data(
                self.metadata_file_path,
                self.input_path,
                self.output_path,
                self.operator,
                self.institution,
                self.instrument,
                self.user_metadata,
                self.batch_id,
            )
            finished_successfully = task_result.get("finished", False) if task_result else False
            self.finished.emit(finished_successfully)
            print("Worker thread finished MTR processing.")
        except Exception:
            print("Unhandled exception in MTR processing thread.")
            self.finished.emit(False)


def process_thermograph_data(
    metadata_file_path,
    input_data_folder_path,
    output_data_folder_path,
    operator,
    institution,
    instrument,
    user_input_metadata,
    batch_id,
):

    global exit_requested
    exit_requested = False
    batch_result_container = {"finished": False}
    # -------------------------------------------------------------
    #  """Process MTR files to generate ODF files."""
    # -------------------------------------------------------------
    start_time = datetime.now()
    print(f"✅ Batch start : {batch_id} ✅ ")
    print(f"MTR Data Processing Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"Data processor: {operator}")
    print(f"Institution: {institution}")
    print(f"Instrument: {instrument}")
    print(f"User metadata: {user_input_metadata}\n")
    print(f"Metadata file: {metadata_file_path}")
    print(f"Input data folder path: {input_data_folder_path}")
    print(f"Output data folder path: {output_data_folder_path}")

    # cwd = os.getcwd()

    try:
        os.chdir(input_data_folder_path)
        print(f"Changed working dir to the input directory: {input_data_folder_path}")
    except Exception as e:
        print(f"Cannot change directory: {e}")
        return batch_result_container

    # Change directory
    if not isinstance(user_input_metadata, dict):
        print(f"user_input_metadata must be dict, got {type(user_input_metadata)}")
        batch_result_container["finished"] = False
        return batch_result_container

    # Look for CSV files
    all_files = Path.glob("*.csv")
    if not all_files:
        print(f"No CSV files found in: {input_data_folder_path}")
        batch_result_container["finished"] = False
        return batch_result_container

    # Prepare output folder
    odf_path = Path(output_data_folder_path / "Step_1_Create_ODF")
    Path.makedir(odf_path, parent=True)
    print(
        f"Created a output data folder name: \
            Step_1_Create_ODF and path for .odf files: {odf_path}"
    )

    # Loop through the CSV files to generate an ODF file for each.
    # for file_name in all_files:
    for idx, file_name in enumerate(all_files, start=1):
        print("")
        print("#######################################################################")
        print(f"=== Start processing MTR file {idx} of {len(all_files)}: {file_name} ===")
        print("#######################################################################")
        print("")

        mtr_path = posixpath.join(input_data_folder_path, file_name)
        print(f"\nProcessing MTR raw file: {mtr_path}\n")

        try:
            mtr = ThermographHeader()

            history_header = HistoryHeader()
            history_header.creation_date = get_current_date_time()
            history_header.set_process(f"INITIAL FILE CREATED BY {operator.upper()}")
            mtr.history_headers.append(history_header)

            mtr.process_thermograph(
                institution, instrument, metadata_file_path, mtr_path, user_input_metadata
            )

            file_spec = mtr.generate_file_spec()
            mtr.file_specification = file_spec
            mtr.add_quality_flags()

            quality_header = QualityHeader()
            quality_header.quality_date = get_current_date_time()
            quality_header.add_quality_codes()
            mtr.quality_header = quality_header

            mtr.update_odf()

            odf_file_path = posixpath.join(odf_path, file_spec + ".ODF")
            print(f"Writing ODF file [{idx}/{len(all_files)}]: {odf_file_path}")
            mtr.write_odf(odf_file_path, version=2.0)
            print(f"SUCCESS: {file_name} → {odf_file_path}")

            # Reset the shared log list
            BaseHeader.reset_log_list()
        except Exception as e:
            print(f"ERROR processing {file_name}: {e}")
            print(traceback.format_exc())
        print("")
        print("#######################################################################")
        print(f"=== End processing MTR file {idx} of {len(all_files)}: {file_name} ===")
        print("#######################################################################")
        print("")

    if idx == len(all_files):
        end_time = datetime.now()
        duration = end_time - start_time
        print(
            f"[{idx}/{len(all_files)}] MTR Data Processing Completed at: \
            {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"Total Processing Time: {str(duration)}")
        print(f"✅ [{idx}/{len(all_files)}] Batch end : {batch_id} ✅ \n")
        print(f"MTR data processing completed for all {len(all_files)} files.")
        batch_result_container["finished"] = True
        return batch_result_container


def run_process_thermograph_data(
    metadata_file_path,
    input_data_folder_path,
    output_data_folder_path,
    operator,
    institution,
    instrument,
    user_input_metadata,
    batch_id,
):

    task_completion = process_thermograph_data(
        metadata_file_path,
        input_data_folder_path,
        output_data_folder_path,
        operator,
        institution,
        instrument,
        user_input_metadata,
        batch_id,
    )

    logger = logging.getLogger("process_mtr_logger")

    if task_completion["finished"]:
        print("Processing Thermograph Data task completed successfully.")
        logger.info("✅ MTR processing completed")
    else:
        print("Processing Thermograph Data task did not complete.......")
    return task_completion


def main_select_inputs():
    app = QApplication.instance()
    must_quit_app = app is None
    if must_quit_app:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    select_inputs = select_metadata_file_and_data_folder.MainWindow()
    select_inputs.show()

    result_container = {
        "finished": False,
        "metadata": None,
        "input": None,
        "output": None,
        "operator": None,
        "institution": None,
        "instrument": None,
        "user_metadata": None,
        "batch_id": None,
    }

    def on_accept():
        metadata_file_path = select_inputs.metadata_file
        input_data_folder_path = select_inputs.input_data_folder
        output_data_folder_path = select_inputs.output_data_folder
        operator = select_inputs.line_edit_text.strip()
        institution = select_inputs.institution.upper()
        instrument = select_inputs.instrument.lower()
        user_input_metadata = select_inputs.user_input_meta

        logger = logging.getLogger("process_mtr_logger")

        if not operator:
            operator, ok = QInputDialog.getText(
                select_inputs,
                "Data processor Name Required",
                "Please enter the name of the analyst performing the data processing:",
            )
            if not ok or not operator.strip():
                logger.warning("❌ Operator name is required. Batch cancelled.")
                return

        if not metadata_file_path or not input_data_folder_path or not output_data_folder_path:
            logger.warning(
                "❌ Missing metadata or input/output folder. "
                "Improper selections made. Please try again. or exiting program....."
            )
            return

        if institution == "BIO":
            match = re.search(r"BCD\d+999", metadata_file_path, re.IGNORECASE)
            if match:
                cruise_number = match.group(0)
            elif "_" in metadata_file_path:
                cruise_number = metadata_file_path.split("_")[1].split(".")[0]
            else:
                cruise_number = metadata_file_path

            batch_id = f"MTR_{cruise_number}_{instrument}_{institution}"

        elif institution == "FSRS":
            pattern = r"\b(LFA)\b\s+(\d+_\d+)"
            match = re.search(pattern, metadata_file_path, re.IGNORECASE)
            if match:
                cruise_number = match.group(1).upper() + "-" + match.group(2).replace("_", "")
            else:
                cruise_number = metadata_file_path
            batch_id = f"MTR_{cruise_number}_{instrument}_{institution}"

        else:
            batch_id = f"MTR_{Path.name(metadata_file_path).split('.')[0]}_{instrument}_{institution}"

        result_container["finished"] = True
        result_container["metadata"] = metadata_file_path
        result_container["input"] = input_data_folder_path
        result_container["output"] = output_data_folder_path
        result_container["operator"] = operator
        result_container["institution"] = institution
        result_container["instrument"] = instrument
        result_container["user_metadata"] = user_input_metadata
        result_container["batch_id"] = batch_id
        select_inputs.close()

    def on_reject():
        print("❌ QC cancelled by user.")
        result_container["finished"] = False
        select_inputs.close()

    select_inputs.buttonBox.accepted.connect(on_accept)
    select_inputs.buttonBox.rejected.connect(on_reject)

    while select_inputs.isVisible():
        app.processEvents()
        time.sleep(0.05)

    if must_quit_app:
        pass

    if result_container["finished"]:
        return (
            result_container["metadata"],
            result_container["input"],
            result_container["output"],
            result_container["operator"],
            result_container["institution"],
            result_container["instrument"],
            result_container["user_metadata"],
            result_container["batch_id"],
        )
    else:
        return None, None, None, None, None, None, None, None


def initialize_mtr_process(log_ui: LogWindowProcessMTR, logger):
    global exit_requested
    exit_requested = False
    logger.info(
        "\n"
        "========================================\n"
        " MTR DATA PROCESSING — INPUT REQUIRED\n"
        "========================================\n"
        "\n"
        "Please provide all required inputs before starting:\n"
        "\n"
        "STEP 1 of 6  ➜ Enter data processor name\n"
        "STEP 2 of 6  ➜ Choose the correct institution (e.g., DFO BIO, FSRS)\n"
        "STEP 3 of 6  ➜ Select the appropriate instrument type\n"
        "STEP 4 of 6  ➜ Select metadata file\n"
        "STEP 5 of 6  ➜ Select input data folder\n"
        "STEP 6 of 6  ➜ Select output data folder\n"
        "\n"
        "ADDITIONAL SETTINGS:\n"
        " • Use default user meta data if not provide appropiate user metadata\n"
        "\n"
        "NEXT:\n"
        " • Click 'Start' to begin processing\n"
        " • Select one batch at a time. After finish start new batch\n"
        "\n"
        "STATUS:\n"
        " • Monitor progress in the terminal\n"
        "\n"
        "========================================"
    )
    logger.info("To Initialize MTR processing please provide all required inputs")

    # Getting User Meta Info)
    (
        metadata_file_path,
        input_path,
        output_path,
        operator,
        institution,
        instrument,
        user_metadata,
        batch_id,
    ) = main_select_inputs()

    if (
        not input_path
        or not output_path
        or not operator
        or not metadata_file_path
        or not institution
        or not instrument
        or not user_metadata
        or not batch_id
    ):
        logger.info("MTR Processing start aborted: missing input, output, or operator.")
        return

    logger.info(
        "Processing Inputs Selected:\n"
        f"  • QC Operator : {operator.strip().title()}\n"
        f"  • Input Path  : {input_path}\n"
        f"  • Output Path : {output_path}\n"
        f"  • Metadata    : {metadata_file_path}\n"
        f"  • Institution : {institution}\n"
        f"  • Instrument  : {instrument}\n"
        f"  • User Metadata: {user_metadata}\n"
        f"  • Batch ID    : {batch_id}\n"
    )

    # Start worker thread
    log_ui.worker = MTRProcessingThread(
        metadata_file_path,
        input_path,
        output_path,
        operator,
        institution,
        instrument,
        user_metadata,
        batch_id,
    )
    log_ui.worker.finished.connect(lambda success: on_mtr_processing_finished(log_ui, success))

    ## Start Worker
    logger.info(
        "\n"
        "=============================================================================================\n"
        "............. MTR DATA PROCESSING STARTED ........ PLEASE WAIT UNTILL FINISHED...............\n"
        "=============================================================================================\n"
        "\n"
    )
    log_ui.worker.start()


def exit_program(app, log_ui):

    logger = logging.getLogger("process_mtr_logger")

    # Signal worker thread to stop (if running)
    if hasattr(log_ui, "worker") and log_ui.worker is not None:
        if log_ui.worker.isRunning():
            # logger.info("Waiting for MTR processing thread to finish...")
            log_ui.worker.requestInterruption()
            log_ui.worker.wait(5000)  # wait up to 5 seconds

    # Flush all handlers
    for handler in logger.handlers:
        try:
            handler.flush()
        except Exception:
            pass

    logger.info("Application exiting.")
    app.quit()


def main_manual_start_qc():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    log_window = LogWindowProcessMTR()
    log_window.show()

    logger = logger_setup()
    # log_listener = attach_gui_logger(logger, log_window.qtext_handler)
    # logger.addHandler(log_window.qtext_handler)
    logger.info("Log window initialized.")
    logger.info("Application started. Click 'Start Processing of MTR Files' to begin.")

    # Connect buttons
    log_window.btn_start.clicked.connect(lambda: initialize_mtr_process(log_window, logger))
    log_window.btn_exit.clicked.connect(lambda: exit_program(app, log_window))

    # Start the Qt event loop
    sys.exit(app.exec())


def logger_setup():
    # exit_requested = False
    logger = logging.getLogger("process_mtr_logger")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler("datashop_MTR_Processing_log.txt", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    logger.info("Logger initialized.")
    return logger


def attach_gui_logger(logger, gui_handler):
    log_queue = queue.Queue()

    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    listener = QueueListener(log_queue, gui_handler)
    listener.start()

    return listener


def on_mtr_processing_finished(log_ui, success):
    logger = logging.getLogger("process_mtr_logger")

    if success:
        logger.info("✅ MTR processing completed successfully.")
    else:
        logger.error("❌ MTR processing failed.")

    log_ui.btn_start.setEnabled(True)

    # 🧹 cleanup
    log_ui.worker.quit()
    log_ui.worker.wait()
    log_ui.worker = None


if __name__ == "__main__":
    main_manual_start_qc()
    # main_automated_start_qc()
