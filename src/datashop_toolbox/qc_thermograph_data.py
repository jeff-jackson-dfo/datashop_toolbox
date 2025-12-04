import glob
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector, Button
from matplotlib.path import Path
import matplotlib.dates as mdates
import numpy as np
import os
import pandas as pd
import pathlib
import sys
import time
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QFileDialog)
from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.validated_base import get_current_date_time
from datashop_toolbox import select_metadata_file_and_data_folder
from datashop_toolbox.log_window import (
    SafeConsoleFilter, QTextEditLogger, 
    SafeConsoleFilter)
import logging

exit_requested = False
global logger
logger = logging.getLogger("datashop")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.addFilter(SafeConsoleFilter())
console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(console_handler)
file_handler = logging.FileHandler("datashop_log.txt", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)
logger.info("Logger initialized.")


class LogWindowUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermograph QC — Log Window")
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        # Log display
        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # Buttons
        self.btn_start = QPushButton("Start QC")
        self.export_button = QPushButton("Export Log")
        self.export_button.clicked.connect(self.export_log)
        self.btn_exit = QPushButton("Exit Program")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.export_button)
        layout.addWidget(self.btn_exit)

        # Attach a QTextEdit-based logger handler to the global logger
        self.qtext_handler = QTextEditLogger(self.log_view)
        logger.addHandler(self.qtext_handler)

        # Small initial message
        self.append_log("📌 Log window initialized.")

    def append_log(self, text: str):
        """Convenience method to append a simple message (and log it)."""
        logger.info(text)

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


def run_qc_thermograph_data(input_path, output_path, qc_operator):
    logger.info(f"Starting QC Thermograph Data task by {qc_operator} on {input_path}")
    wildcard = "*.ODF"
    task_completion= qc_thermograph_data(input_path, wildcard, output_path, qc_operator)
    if task_completion["finished"]:
        logger.info(f"✅ QC Thermograph Data task completed successfully.")
    else:
        print("❌ QC Thermograph Data task did not complete.")
    return task_completion
   
    
def qc_thermograph_data(in_folder_path: str, wildcard: str, out_folder_path: str, qc_operator: str):
    """
    Processes ODF files in `in_folder_path` matching `wildcard`, writes to out_folder_path/Step_2_Quality_Flagging.
    Uses global `exit_requested` to allow user interruption.
    Returns {"finished": bool}
    """
    
    global exit_requested
    exit_requested = False
    batch_result_container = {"finished": False}

    cwd = os.getcwd()

    try:
        os.chdir(in_folder_path)
        logger.info(f"Changed working dir to the input directory: {in_folder_path}")
    except Exception as e:
        logger.exception(f"Cannot change directory: {e}")
        return batch_result_container
    
    mtr_files = glob.glob(wildcard)
    if not mtr_files:
        logger.warning("No ODF files found in selected folder.")
        os.chdir(cwd)
        return batch_result_container


    # Prepare output folder
    out_odf_path = os.path.join(out_folder_path, "Step_2_Quality_Flagging")
    os.makedirs(out_odf_path, exist_ok=True)
    logger.info(f"Created a output data folder name, Step_2_Quality_Flagging ")
    logger.info(f"Path for Step_2_Quality_Flagging: {out_odf_path}")

    os.chdir(cwd)

    for idx, mtr_file in enumerate(mtr_files, start=1):
        if exit_requested:
            logger.warning("Exit requested — stopping QC loop.")
            break
        
        logger.info(f"✅ Reading file {idx} of {len(mtr_files)}: {mtr_file}")
        logger.info(f"✅ Please wait...reading ODF file for QC visualization...")

        full_path = str(pathlib.Path(in_folder_path, mtr_file))
        
        try:
            mtr = ThermographHeader()
            mtr.read_odf(full_path)
        except Exception as e:
            logger.exception(f"Failed to read ODF {full_path}: {e}")
            continue

        orig_df = mtr.data.data_frame

        # Extract temperature and time
        temp = orig_df['TE90_01'].to_numpy()
        sytm = orig_df['SYTM_01'].str.lower().str.strip("'")
        try:
            dt = pd.to_datetime(sytm, format='%d-%b-%Y %H:%M:%S.%f')
        except Exception:
            dt = pd.to_datetime(sytm, infer_datetime_format=True, errors="coerce")

        # Create a DataFrame with Temperature as the variable and DateTime as the index.
        df = pd.DataFrame({'Temperature': temp}, index=dt)

        # Convert datetime to numeric for lasso selection
        xy = np.column_stack([mdates.date2num(df.index.to_pydatetime()), df['Temperature']])

        # Store multiple selection groups
        selection_groups = []

        # Plot the temperature time series
        fig, ax = plt.subplots(figsize=(10, 6))
        pts = ax.scatter(df.index, df['Temperature'], s=10, color='blue')
        plt.title(f'[{idx}/{len(mtr_files)}] Time Series Data- {mtr_file}')
        plt.xlabel('Date Time')
        plt.ylabel('Temperature')
        plt.grid(True)

        # --- Buttons (tuple positions required in Python 3.13+) ---
        ax_deselect = plt.axes((0.02, 0.01, 0.12, 0.06))
        ax_continue = plt.axes((0.70, 0.01, 0.12, 0.06))
        ax_exit = plt.axes((0.85, 0.01, 0.12, 0.06))

        btn_deselect = Button(ax_deselect, "Undo Selection")
        btn_continue = Button(ax_continue, "Continue")
        btn_exit = Button(ax_exit, "Exit")
        
        # --- Optional visual tweaks ---
        btn_continue.color = "lightgreen"
        btn_exit.color = "salmon"
        btn_continue.hovercolor = "limegreen"
        btn_exit.hovercolor = "red"
        btn_deselect.color = "lightblue"
        btn_deselect.hovercolor = "yellow"

        def click_continue(event):
            logger.info("Figure: Continue clicked.")
            plt.close(fig)  # close figure and continue

        def click_exit(event):
            global exit_requested
            exit_requested = True
            logger.info("Figure: Exit clicked (exit_requested set True).")
            plt.close(fig)  # close figure and stop

        def undo_selection(event):
            """Clear all selected groups and redraw original plot."""
            selection_groups.clear()  # Remove all previously selected regions
            logger.info("Figure: Undo Selection clicked (all selections cleared).")
            # Reset axes
            ax.cla()

            # Replot original blue data points
            nonlocal  scatter_blue
            scatter_blue = ax.scatter(df.index, df['Temperature'], s=10, color='blue', picker=5)
            ax.set_title(f'[{idx}/{len(mtr_files)}] Time Series Data - {mtr_file}')
            ax.set_xlabel('Date Time')
            ax.set_ylabel('Temperature')
            ax.grid(True)
            fig.canvas.mpl_connect('pick_event', on_pick)

            # Recreate the lasso tool since clearing breaks it
            nonlocal lasso   # allow access to outer variable
            try:
                lasso.disconnect_events()
            except Exception:
                pass
            lasso = LassoSelector(ax, onselect)

            fig.canvas.draw_idle()
        
        btn_continue.on_clicked(click_continue)
        btn_exit.on_clicked(click_exit)
        btn_deselect.on_clicked(undo_selection)

        def on_pick(event):
            if event.artist != scatter_blue:
                return
            ind = event.ind
            if len(ind) == 0:
                return
            logger.info(f"Selected {len(ind)} point(s) via CLICK.")
            
            selected_indices = ind
            selected_points = xy[selected_indices]
            ax.scatter(selected_points[:, 0], selected_points[:, 1],
                   color='red', s=30, zorder=3)
            plt.draw()
            selected_dt = list(mdates.num2date(selected_points[:, 0]))
            selected_temp = selected_points[:, 1].tolist()
            selected_df = pd.DataFrame({
                        "DateTime": selected_dt,
                        "Temperature": selected_temp,
                        "idx": selected_indices})
            selection_groups.append(selected_df)
            
        def onselect(verts):
            path = Path(verts)
            selected_indices = np.nonzero(path.contains_points(xy))[0]
            if selected_indices.size == 0:
                return
            logger.info(f"Selected {len(selected_indices)} point(s) via LASSO")
            selected_points = xy[selected_indices]
            ax.scatter(mdates.num2date(selected_points[:, 0]), selected_points[:, 1], color='red', s=20)
            plt.draw()

            # Store selected points
            selected_dt = list(mdates.num2date(selected_points[:, 0]))
            selected_temp = selected_points[:, 1].tolist()
            selected_df = pd.DataFrame({
                'DateTime': selected_dt, 
                'Temperature': selected_temp, 
                'idx': selected_indices})
            selection_groups.append(selected_df)
            
        fig.canvas.mpl_connect("pick_event", on_pick)
        scatter_blue = ax.scatter(df.index, df['Temperature'], s=10, color='blue', picker=5)

        lasso = LassoSelector(ax, onselect)
        
        ## Plt show non-blocking
        plt.show(block=False)
        
        # Wait until the figure is closed, processing Qt events so the main GUI remains responsive
        app = QApplication.instance()
        while plt.fignum_exists(fig.number) and not exit_requested:
            if app:
                app.processEvents()
            time.sleep(0.05)

        # After closing the plot and collecting all selection groups
        if selection_groups:
            combined_indices = np.unique(
                np.concatenate([g['idx'].to_numpy() for g in selection_groups])).astype(int)
            logger.info(f"Total of {len(combined_indices)} unique points selected for flagging.")
            
            logger.info("Flagging selected points with QTE90_01 = 4, others with QTE90_01 = 1.")
            index_labels_to_flag = orig_df.index[combined_indices]
            orig_df.loc[index_labels_to_flag, 'QTE90_01'] = 4
            orig_df.loc[~orig_df.index.isin(index_labels_to_flag), 'QTE90_01'] = 1
            logger.info(f"✔ Flagged {len(index_labels_to_flag)} points in {mtr_file}")  
        else:
            orig_df['QTE90_01'] = 1
            logger.info("No points were selected for this file.")

        # Output revised ODF
        try:
            mtr.data.data_frame = orig_df
            mtr.add_history()
            mtr.add_to_history(f'ADD QUALITY FLAG AND PERFORM VISUAL QC BY {qc_operator.upper()}')
            mtr.update_odf()
            file_spec = mtr.generate_file_spec()
            mtr.file_specification = file_spec
            logger.info(f"Writing file {idx} of {len(mtr_files)}: {mtr_file}")
            logger.info(f"Please wait...writing QC ODF file...")
            out_file = pathlib.Path(out_odf_path) / f"{file_spec}.ODF"
            mtr.write_odf(str(out_file), version=2.0)
            logger.info(f"✔ QC completed for [{idx}/{len(mtr_files)}]: {mtr_file}")
            logger.info(f"    → Saved [{idx}/{len(mtr_files)}]: {out_file}")
        except Exception as e:
            logger.exception(f"Failed writing QC ODF for {mtr_file}: {e}")

    # Completed loop
    if not exit_requested and (idx == len(mtr_files)):
        logger.info(f"🎉 QC process completed for all {len(mtr_files)} files.")
        batch_result_container["finished"] = True
    elif exit_requested:
        logger.info(f"⚠️ QC process was interrupted before completion ({idx} of {len(mtr_files)} files).")
        batch_result_container["finished"] = False
    else:
        # fallback
        batch_result_container["finished"] = False

    return batch_result_container


def main_select_inputs():
    app = QApplication.instance()
    must_quit_app = app is None
    if must_quit_app:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    select_inputs = select_metadata_file_and_data_folder.SubWindowOne()
    select_inputs.show()

    result_container = {"finished": False, "input": None, "output": None, "operator": None}

    
    def on_accept():
        operator = select_inputs.qc_name.strip()
        input_path = select_inputs.input_data_folder
        output_path = select_inputs.output_data_folder

        if not operator or not input_path or not output_path:
            print("❌ Missing required fields.")
            return

        result_container["operator"] = operator
        result_container["input"] = input_path
        result_container["output"] = output_path
        result_container["finished"] = True
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
            result_container["input"],
            result_container["output"],
            result_container["operator"],
        )
    else:
        return None, None, None


def exit_program(app):
    """
    Clean exit.
    """
    global exit_requested
    exit_requested = True
    logger.info("Exit Program clicked — setting exit_requested and quitting.")
    # Allow logger to flush
    handlers = logger.handlers[:]
    for h in handlers:
        try:
            h.flush()
        except Exception:
            pass
    app.quit()


def start_qc_process(log_ui: LogWindowUI):
    """
    Called when Start QC button is clicked.
    It opens the metadata/input selection dialog, and if accepted, runs the QC workflow.
    """
    global exit_requested
    exit_requested = False
    logger.info("Start QC button clicked.")
    input_path, output_path, operator = main_select_inputs()
    if not input_path or not output_path or not operator:
        logger.info("QC start aborted: missing input, output, or operator.")
        return
    logger.info(f"Inputs selected: operator={operator}, input={input_path}, output={output_path}")
    run_qc_thermograph_data(input_path, output_path, operator)
    logger.info("Finished batch successfully (returned to GUI).")
    logger.info("Please Start QC for new batch.")


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    log_window = LogWindowUI()
    log_window.show()

    # Connect buttons
    log_window.btn_start.clicked.connect(lambda: start_qc_process(log_window))
    log_window.btn_exit.clicked.connect(lambda: exit_program(app))
    logger.info("Application started. Use Start QC to begin.")

    # Start the Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    
















