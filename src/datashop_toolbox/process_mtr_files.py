import glob
import os
import posixpath
import sys
import re
import traceback
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QInputDialog
)
from PyQt6.QtCore import QTimer

from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.validated_base import get_current_date_time
from datashop_toolbox import select_metadata_file_and_data_folder
from datashop_toolbox.qualityhdr import QualityHeader
from datashop_toolbox.log_window import LogWindow, Worker


def process_mtr_files_for_worker(
        log,
        metadata_file_path,
        input_data_folder_path,
        output_data_folder_path,
        operator,
        institution,
        instrument,
        batch_ID,
        user_input_metadata
    ):
    # -------------------------------------------------------------
    #  """Process MTR files to generate ODF files."""
    # -------------------------------------------------------------
    start_time = datetime.now()
    log(f"✅ Batch start : {batch_ID} ✅ ")
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
    all_files = glob.glob("*.csv") 
    if not all_files:
        log(f"No CSV files found in: {input_data_folder_path}")
        return
    
    # Prepare output folder
    odf_path = os.path.join(output_data_folder_path, "Step_1_Create_ODF")
    os.makedirs(odf_path, exist_ok=True)
    log(f"Created a output data folder name: Step_1_Create_ODF and path for .odf files: {odf_path}")

     # Loop through the CSV files to generate an ODF file for each.
    #for file_name in all_files:
    for idx, file_name in enumerate(all_files, start=1):

        log("")
        log('#######################################################################')
        log(f'=== Start processing MTR file {idx} of {len(all_files)}: {file_name} ===')
        log('#######################################################################')
        log("")

        mtr_path = posixpath.join(input_data_folder_path, file_name)
        log(f'\nProcessing MTR raw file: {mtr_path}\n')

        try:

            mtr = ThermographHeader()

            history_header = HistoryHeader()
            history_header.creation_date = get_current_date_time()
            history_header.set_process(f'INITIAL FILE CREATED BY {operator.upper()}')
            mtr.history_headers.append(history_header)

            mtr.process_thermograph(institution, instrument, metadata_file_path, mtr_path, user_input_metadata)

            file_spec = mtr.generate_file_spec()
            mtr.file_specification = file_spec
            mtr.add_quality_flags()
    
            quality_header = QualityHeader()
            quality_header.quality_date = get_current_date_time()
            quality_header.add_quality_codes()
            mtr.quality_header = quality_header

            mtr.update_odf()

            odf_file_path = posixpath.join(odf_path, file_spec + '.ODF')
            log(f"Writing ODF file [{idx}/{len(all_files)}]: {odf_file_path}")
            mtr.write_odf(odf_file_path, version = 2.0)
            log(f"SUCCESS: {file_name} → {odf_file_path}")

            # Reset the shared log list
            BaseHeader.reset_log_list()
        except Exception as e:
            log(f"ERROR processing {file_name}: {e}")
            log(traceback.format_exc())
        log("")
        log('#######################################################################')
        log(f'=== End processing MTR file {idx} of {len(all_files)}: {file_name} ===')
        log('#######################################################################')
        log("")
    
    if idx == len(all_files):
        end_time = datetime.now()
        duration = end_time - start_time
        log(f"[{idx}/{len(all_files)}] MTR Data Processing Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"Total Processing Time: {str(duration)}")
        log(f"✅ [{idx}/{len(all_files)}] Batch end : {batch_ID} ✅ \n")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Create log window first
    log_window = LogWindow()
    log_window.show()
    log_window.redirect_prints_to_log()
    print("""
    Please provide all the required inputs to process MTR data:
    First - Enter data processor name (Step 1 of 4), select metadata file (Step 2 of 4), input data folder (Step 3 of 4),
            output data folder (Step 4 of 4), 
    Second - Choose institution, instrument, and user meta info according to the data being processed.
    Third - Click 'Start' to begin processing. You can process multiple batches sequentially.
    Finally - Monitor progress in this log window.
    """.strip())
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
            except:
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
        except:
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
            #Read values from UI
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
                    "Please enter the name of the analyst performing the data processing:"
                )
                if not ok or not operator.strip():
                    log_window.write("❌ Operator name is required. Batch cancelled.")
                    return
            
            if not metadata_file_path or not input_data_folder_path or not output_data_folder_path:
                log_window.write("❌ Missing metadata or input/output folder. Improper selections made. Please try again. or exiting program.....")
                return

            if institution == 'BIO':
                match = re.search(r"BCD\d+999", metadata_file_path, re.IGNORECASE)
                if match:
                    cruise_number = match.group(0)
                elif "_" in metadata_file_path: 
                    cruise_number = metadata_file_path.split("_")[1].split(".")[0]
                else:
                    cruise_number = metadata_file_path
                
                batch_ID = f"MTR_{cruise_number}_{instrument}_{institution}"
            
            elif institution == 'FSRS':
                pattern = r"\b(LFA)\b\s+(\d+_\d+)"
                match = re.search(pattern, metadata_file_path, re.IGNORECASE)
                if match:
                    cruise_number = match.group(1).upper() +'-' + match.group(2).replace("_", "")
                else:
                    cruise_number = metadata_file_path
                batch_ID = f"MTR_{cruise_number}_{instrument}_{institution}"
            
            else:
                batch_ID = f"MTR_{os.path.basename(metadata_file_path).split('.')[0]}_{instrument}_{institution}"
                      
            # Start worker thread
            worker = Worker(
                process_mtr_files_for_worker,
                metadata_file_path,
                input_data_folder_path,
                output_data_folder_path,
                operator,
                institution,
                instrument,
                batch_ID,
                user_input_metadata
            )

            log_window.active_workers.append(worker)
            worker.log.connect(log_window.write)

            def on_success():
                log_window.write(f"\n✅ ✅ ✅ <<< Batch completed successfully. Please select next batch to continue >>> ✅ ✅ ✅ \n")
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
    
if __name__ == "__main__":

    main()
