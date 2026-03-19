# Import standard libraries
import getpass
import json
import sys
from datetime import datetime
from icecream import ic
from pathlib import Path
from dataclasses import dataclass, fields
from enum import Enum

# Import external libraries
import numpy as np
import pandas as pd
from pyrsktools import RSK
from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow
from termcolor import colored

import seabirdscientific.conversion as conv
import seabirdscientific.processing as proc
import seabirdscientific.utils as utils

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.lookup_parameter import lookup_parameter
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.parameterhdr import ParameterHeader
from datashop_toolbox.read_seaodf_parameters import read_seaodf_parameters

# Import custom children dialogs
from odf_metadata_dialog import OdfMetadataDialog
from rbr_profile_plot import PlotDialog

# Important:
# You need to run the following command to generate the Ui_main_window.py file:
#    pyside6-uic rbr_to_odf.ui -o Ui_main_window.py
from ui_rbr_to_odf import Ui_main_window

@dataclass
class BtlHeader():
    """Bottle header information to export BTL file."""
    ship: str
    cruise: str
    latitude: float
    longitude: float
    sounding: float
    event_number: int
    cast: int
    station_name: str
    event_comments: str
    instrument_serial_number: str

    def __str__(self) -> str:
        lines = [f"* ** {f.name.title()}: {getattr(self, f.name)}" for f in fields(self)]
        return "\n".join(lines)


class MainWindow(QMainWindow):
    class Position_Type(Enum):
        LAT = 'latitude'
        LON = 'longitude'

    def __init__(self, parent=None):
        super().__init__(parent)

        # =====================================================
        # PHASE 1 — DEFINE ALL STATE (must come first)
        # =====================================================
        self._rsk_folder: str = ""
        self._rsk_file: str = ""
        self._restoring_state: bool = True
        self._odf = OdfHeader()
        self._odf_folder: str = ""
        self._config_path = Path.home() / ".rsk_profile_gui.json"
        self._saved_profile_indices: list[int] = []  # indices selected in the Plot dialog (0-based)
        self._plot_profiles_dialog = None  # Save the last dialog ref if you want to overlay later
        self._btl = BtlHeader(
            ship="Unknown",
            cruise="Unknown",
            latitude=-999.0,
            longitude=-999.0,
            sounding=-999.0,
            event_number=0,
            cast=0,
            station_name="Unknown",
            event_comments="",
            instrument_serial_number="Unknown"
        )

        # =====================================================
        # PHASE 2 — BUILD UI
        # =====================================================
        self.ui = Ui_main_window()
        self.ui.setupUi(self)

        # Validators
        self._setup_validators()

        # =====================================================
        # PHASE 3 — RESTORE SAVED STATE (NO SIGNALS)
        # =====================================================
        self._load_settings()

        # =====================================================
        # PHASE 4 — CONNECT SIGNALS (USER INTERACTION ONLY)
        # =====================================================
        self._connect_signals()

        self._restoring_state = False

    def _setup_validators(self):
        self.ui.latitude_line_edit.setPlaceholderText("###.######")
        self.ui.longitude_line_edit.setPlaceholderText("####.######")

        latitude_validator = QDoubleValidator(-90.0, 90.0, 6)
        longitude_validator = QDoubleValidator(-180.0, 180.0, 6)

        locale = QLocale(QLocale.English, QLocale.UnitedStates)
        latitude_validator.setLocale(locale)
        longitude_validator.setLocale(locale)

        latitude_validator.setNotation(QDoubleValidator.StandardNotation)
        longitude_validator.setNotation(QDoubleValidator.StandardNotation)

        self.ui.latitude_line_edit.setValidator(latitude_validator)
        self.ui.longitude_line_edit.setValidator(longitude_validator)

    def _connect_signals(self):
        self.ui.select_folder_push_button.clicked.connect(self._choose_rsk_folder)
        self.ui.profile_plots_push_button.clicked.connect(self._profile_plots)
        self.ui.clear_info_push_button.clicked.connect(self._clear_settings)
        self.ui.edit_metadata_push_button.clicked.connect(self._edit_metadata)
        self.ui.export_odf_push_button.clicked.connect(self._export_odf)
        self.ui.export_btl_push_button.clicked.connect(self._export_btl)
        self.ui.exit_push_button.clicked.connect(QApplication.instance().quit)
        self.ui.rsk_list_widget.currentItemChanged.connect(self._on_rsk_selected)

    @property
    def rsk_file_path(self) -> str:
        if not self._rsk_folder or not self._rsk_file:
            return ""
        path = str(Path(self._rsk_folder) / self._rsk_file)
        return path

    def _on_rsk_selected(self, current, previous):
        if self._restoring_state or not current:
            return
        self._rsk_file = current.text()
        self._update_channel_list()

    def _save_settings(self):
        data = {
            "folder": self.ui.folder_line_edit.text(),
            "latitude": self.ui.latitude_line_edit.text(),
            "longitude": self.ui.longitude_line_edit.text(),
            "selected_rsk": (
                self.ui.rsk_list_widget.currentItem().text()
                if self.ui.rsk_list_widget.currentItem()
                else None
            ),
            "selected_channels": [
                item.text() for item in self.ui.channel_list_widget.selectedItems()
            ],
            "window": {"geometry": bytes(self.saveGeometry()).hex()},
        }

        try:
            with self._config_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            colored(f"Failed to save settings: {e}", 'light_red')

    def _load_settings(self):
        if not self._config_path.exists():
            return

        try:
            with self._config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            colored(f"Failed to load settings: {e}", 'light_red')
            return

        self.ui.rsk_list_widget.blockSignals(True)

        # Folder + file list
        folder = data.get("folder", "")
        if folder and Path(folder).exists():
            self._rsk_folder = folder
            self.ui.folder_line_edit.setText(folder)

            self.ui.rsk_list_widget.clear()
            rsk_files = sorted(
                p.name for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() == ".rsk"
            )
            self.ui.rsk_list_widget.addItems(rsk_files)

        # Restore selection
        self._rsk_file = data.get("selected_rsk", "")
        if self._rsk_file:
            matches = self.ui.rsk_list_widget.findItems(self._rsk_file, Qt.MatchExactly)
            if matches:
                self.ui.rsk_list_widget.setCurrentItem(matches[0])

        self.ui.rsk_list_widget.blockSignals(False)

        # Manual post-restore update
        if self._rsk_file:
            self._update_channel_list()

        # Lat / Lon
        self.ui.latitude_line_edit.setText(data.get("latitude", ""))
        self.ui.longitude_line_edit.setText(data.get("longitude", ""))

        # Window geometry
        geometry_hex = data.get("window", {}).get("geometry")
        if geometry_hex:
            self.restoreGeometry(bytes.fromhex(geometry_hex))

    def close_event(self, event):
        self._save_settings()
        super().closeEvent(event)

    def _choose_rsk_folder(self):

        folder_path = QFileDialog.getExistingDirectory(
            self, "Select the folder containing the RSK files", dir="."
        )
        if folder_path:
            # Remove any previous items from the list widgets
            self.ui.rsk_list_widget.clear()
            self.ui.channel_list_widget.clear()

            # Display the selected folder path
            self.ui.folder_line_edit.setText(folder_path)
            self._rsk_folder = folder_path
            rsk_files = sorted(
                p for p in Path(folder_path).iterdir() if p.is_file() and p.suffix.lower() == ".rsk"
            )
            rsk_paths = [Path(p).name for p in rsk_files]
            self.ui.rsk_list_widget.addItems(rsk_paths)

    # Update the channel_list_widget when a RSK file is selected
    def _update_channel_list(self):
        self.ui.channel_list_widget.clear()

        try:
            with RSK(self.rsk_file_path) as rsk:
                rsk.readdata()
                channels = rsk.channelNames

            self.ui.channel_list_widget.addItems(channels)

            # Restore previously selected channels
            if self._config_path.exists():
                with self._config_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                selected = set(data.get("selected_channels", []))
                for i in range(self.ui.channel_list_widget.count()):
                    item = self.ui.channel_list_widget.item(i)
                    if item.text() in selected:
                        item.setSelected(True)

        except Exception as e:
            self.ui.channel_list_widget.addItem(f"Error reading RSK: {e}")

    def _profile_plots(self):
        fig_list = []
        channels_to_plot = []

        # Build figures
        with RSK(self.rsk_file_path) as rsk:
            rsk.readdata()

            # Select channels / derive as needed
            if "temperature" in rsk.channelNames:
                channels_to_plot.append("temperature")

            if "pressure" in rsk.channelNames:
                if "seapressure" not in rsk.channelNames:
                    rsk.deriveseapressure()

            if "conductivity" in rsk.channelNames:
                channels_to_plot.append("conductivity")
                if "salinity" not in rsk.channelNames:
                    rsk.derivesalinity()

            if "salinity" in rsk.channelNames:
                channels_to_plot.append("salinity")
                rsk.derivesigma()
                channels_to_plot.append("density_anomaly")

            # Dissolved O2 channel if present
            if "dissolved_o2_concentration" in rsk.channelNames:
                channels_to_plot.append("dissolved_o2_concentration")
            elif "dissolved_o2_saturation" in rsk.channelNames:
                channels_to_plot.append("dissolved_o2_saturation")

            # Compute profiles and collect a figure per profile
            rsk.computeprofiles(pressureThreshold=3.0, conductivityThreshold=0.05)
            profiles = rsk.getprofilesindices()

            for p, profile_indices in enumerate(profiles):
                fig, axes = rsk.plotprofiles(
                    channels=channels_to_plot,
                    profiles=(p, p),
                    direction="down",
                )
                fig_list.append(fig)

        # ---- Open ONE dialog with ALL figures, after the loop ----
        if fig_list:
            self._plot_profiles_dialog = PlotDialog(
                fig_handles=fig_list, parent=self, title="RSK Profiles"
            )
            self._plot_profiles_dialog.exec()

       
    def _clear_settings(self):
        # Clear all widgets
        self.ui.folder_line_edit.clear()
        self.ui.rsk_list_widget.clear()
        self.ui.channel_list_widget.clear()
        self.ui.latitude_line_edit.clear()
        self.ui.longitude_line_edit.clear()


    def _edit_metadata(self):
        msg = colored("Editing ODF metadata ...", 'cyan')
        print(msg)
        dlg = OdfMetadataDialog(self)  # parent = MainWindow

        if dlg.exec():
            self._odf = dlg.odf()
            if self._odf is not None:
                # Use it: save, serialize, pass to pipeline, etc.
                msg = colored("ODF object received by MainWindow", 'green')
                print(msg)
            else:
                msg = colored("Export cancelled", 'red')
                print(msg)
        else:
            # Dialog cancelled
            msg = colored("ODF export cancelled", 'red')
            print(msg)


    @staticmethod
    def _split_string_get_end_number(s):
        digits = ""
        for i in range(len(s) - 1, -1, -1):
            if s[i].isdigit():
                digits = s[i] + digits
            else:
                break

        if not digits:
            return [s]

        return [s[: -len(digits)], digits]


    def _populate_parameter_headers(self, df: pd.DataFrame) -> dict:
        """Populate the parameter headers and the data object."""
        parameter_headers = list()
        parameter_dict = dict()
        parameter_list = list()
        print_formats = dict()
        number_of_rows = df.count().iloc[0]
        param_name = ""
        for column in df.columns:
            parameter_number = 0
            if column.startswith("temperature"):
                pass
            # Split column name string if it has at least one trailing numeric value
            parts = self._split_string_get_end_number(column)
            column = parts[0]
            if len(parts) > 1:
                parameter_number = int(parts[1])
            parameter_header = ParameterHeader()
            number_null = int(df[column].isnull().sum())
            number_valid = int(number_of_rows - number_null)
            if column == "timestamp":
                param_name = "SYTM"
                param_code = f"{param_name}_01"
                parameter_header.type = param_name
                # Convert datetime values to SYTM strings
                sytm = df[column].dt.strftime(BaseHeader.SYTM_FORMAT).to_list()
                sytm_strings = [t[:-4].upper() for t in sytm]
                min_date = sytm_strings[0]
                max_date = sytm_strings[-1]
                parameter_header.minimum_value = min_date
                parameter_header.maximum_value = max_date
                parameter_header.null_string = BaseHeader.SYTM_NULL_VALUE
                df[column] = [f"'{s}'" for s in sytm_strings]
            elif column == "sample":
                param_name = "CNTR"
                parameter_header.type = "INTE"
            elif column == "nbin":
                param_name = "SNCN"
                parameter_header.type = "INTE"
            elif column == "pressure":
                param_name = "TOTP"
                parameter_header.type = "DOUB"
            elif column == "sea_pressure":
                param_name = "PRES"
                parameter_header.type = "DOUB"
            elif column == "depth":
                param_name = "DEPH"
                parameter_header.type = "DOUB"
            elif column == "temperature":
                param_name = "TE90"
                parameter_header.type = "DOUB"
            elif column == "conductivity":
                param_name = "CNDC"
                parameter_header.type = "DOUB"
            elif column == "salinity":
                param_name = "PSAL"
                parameter_header.type = "DOUB"
            elif column == "density_anomaly":
                param_name = "SIGP"
                parameter_header.type = "DOUB"
            elif column == "speed_of_sound":
                param_name = "SVEL"
                parameter_header.type = "DOUB"
            elif column == "dissolved_o2_concentration":
                param_name = "DOXC"
                parameter_header.type = "DOUB"
            elif column == "dissolved_o2_saturation":
                param_name = "OSAT"
                parameter_header.type = "DOUB"
            elif column == "scans_per_bin":
                param_name = "SNCN"
                parameter_header.type = "INTE"
            elif column == "specific_conductivity":
                continue
            if parameter_header.type == "DOUB" or parameter_header.type == "INTE":
                param_code = f"{param_name}_{parameter_number + 1:02d}"
                min_temp = df[column].min()
                max_temp = df[column].max()
                parameter_header.minimum_value = min_temp
                parameter_header.maximum_value = max_temp
                parameter_header.null_string = str(BaseHeader.NULL_VALUE)

            parameter_info = lookup_parameter("sqlite", param_name)
            parameter_header.name = parameter_info.get("description")
            parameter_header.units = parameter_info.get("units")
            parameter_header.code = param_code
            parameter_header.angle_of_section = BaseHeader.NULL_VALUE
            parameter_header.magnetic_variation = BaseHeader.NULL_VALUE
            parameter_header.depth = BaseHeader.NULL_VALUE
            if parameter_header.units == "GMT":
                parameter_header.print_field_width = parameter_info.get("print_field_width")
                parameter_header.print_decimal_places = parameter_info.get("print_decimal_places")
                print_formats[param_code] = f"{parameter_header.print_field_width}"
            else:
                parameter_header.print_field_width = parameter_info.get("print_field_width")
                parameter_header.print_decimal_places = parameter_info.get("print_decimal_places")
                print_formats[param_code] = (
                    f"{parameter_header.print_field_width}.{parameter_header.print_decimal_places}"
                )
            parameter_header.number_valid = number_valid
            parameter_header.number_null = number_null
            parameter_list.append(param_code)

            # Add the new parameter header to the list.
            parameter_headers.append(parameter_header)

        # Update the data object.
        parameter_dict["parameter_headers"] = parameter_headers
        parameter_dict["parameter_list"] = parameter_list
        parameter_dict["print_formats"] = print_formats
        if "specific_conductivity" in df.columns:
            df = df.drop("specific_conductivity", axis=1)
        df.columns = parameter_list
        parameter_dict["data_frame"] = df

        return parameter_dict

    def _choose_export_odf_folder(self) -> str:

        odf_folder_path = QFileDialog.getExistingDirectory(
            self, "Select the folder to save the ODF file(s)", dir="."
        )
        if odf_folder_path:
            # Display the selected folder path
            self.ui.odf_folder_line_edit.setText(odf_folder_path)

        return odf_folder_path


    @staticmethod
    def round_to_nearest_half(number):
        return round(number * 2) / 2


    def _export_odf(self):
        msg = colored("Preparing to export to ODF ...", 'yellow')
        print(msg)

        # Choose output folder once
        odf_export_folder = self._choose_export_odf_folder()
        if not odf_export_folder:
            print(colored("Export cancelled (no folder selected).", 'red'))
            return

        with RSK(self.rsk_file_path) as rsk:

            rsk.readdata()
            raw = rsk.data.copy()  # Keep a copy of the raw data if needed for reference

            # Compute profiles once; we will query by direction below
            rsk.computeprofiles(pressureThreshold=3.0, conductivityThreshold=0.05)

            # Derived channels needed once
            if "salinity" in rsk.channelNames:
                rsk.derivesigma()

            # Required shift of C relative to T for each profile
            lag = rsk.calculateCTlag(seapressureRange = (1,100), direction = "down")
            # Advance temperature
            lag = -np.array(lag)
            # Select best lag for consistency among profiles
            lag = np.median(lag).round().astype(int)
            rsk.alignchannel(channel = "temperature", lag = lag, direction = "down")

            rsk.smooth(channels = ["salinity", "density_anomaly"], windowLength = 5)

            # bin_count = rsk.binaverage(
            #     binBy = "sea_pressure",
            #     binSize = 0.5,
            #     boundary = 0.25,
            #     direction = 'down'
            # )
            # rsk.addchannel(data=bin_count, channel="scans_per_bin", units=None)

            scan_number = list(range(1, len(rsk.data["pressure"]) + 1))
            rsk.addchannel(data=scan_number, channel="sample", units=None)

            # Update the INSTRUMENT_HEADER once (static metadata)
            self._odf.instrument_header.instrument_type = "RBR"
            self._odf.instrument_header.model = rsk.instrument.model
            self._odf.instrument_header.serial_number = str(rsk.instrument.serialID)

            # Creation dates once per export session
            current_dt = datetime.now().strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
            self._odf.event_header.creation_date = current_dt
            self._odf.event_header.orig_creation_date = current_dt

            # Sampling interval if missing
            if self._odf.event_header.sampling_interval < 0:
                self._odf.event_header.sampling_interval = rsk.scheduleInfo.samplingperiod()

            # Gather user-saved profile indices once (if any)
            saved = []
            if self._plot_profiles_dialog is not None:
                saved = self._plot_profiles_dialog.get_saved_profiles() or []
            self._saved_profile_indices = saved
            print(colored(f"Saved profile indices for export: {self._saved_profile_indices}", 'cyan'))

            for cast_direction in ["down", "up"]:

                # Set event qualifier and suffix for filename
                if cast_direction == "down":
                    self._odf.event_header.event_qualifier2 = "DN"
                    cast_type = 'DOWNCAST'
                else:
                    self._odf.event_header.event_qualifier2 = "UP"
                    cast_type = 'UPCAST'

                # Subset to selected profiles for THIS direction (if any were saved)
                if self._saved_profile_indices:

                    profiles = rsk.getprofilesindices(direction=cast_direction)  # list of arrays
                    if not profiles:
                        print(colored(f"No {cast_direction} profiles found; skipping.", 'red'))
                        continue
                    
                    # Filter profiles to only those selected in the Plot dialog
                    profiles = [idx for i, idx in enumerate(profiles) if i in self._saved_profile_indices]

                    print(colored(f"Exporting {len(profiles)} {cast_direction} profile based on user selection.", 'green'))

                    for p, profile_idx in enumerate(profiles):

                        # print(f"Profile {p} indices being exported for {cast_direction}: {profile_idx}")

                        df = pd.DataFrame(rsk.data)

                        # Subset to THIS profile for THIS direction
                        profile_df = df.iloc[profile_idx]

                        # print(profile_df.head())

                        xr_profile_df = profile_df.to_xarray()

                        # Use bin_average from seabirdscientific.processing to bin the data for this profile
                        profile_xarray = proc.bin_average(xr_profile_df, bin_variable="sea_pressure", bin_size=0.5, include_scan_count=True, cast_type=cast_type)
                        binned_profile_df = profile_xarray.to_dataframe()

                        binned_profile_df['sea_pressure'] = self.round_to_nearest_half(binned_profile_df['sea_pressure'])

                        # print(binned_profile_df.head())

                        # Populate parameter headers & data object for THIS cast and direction
                        parameter_dict = self._populate_parameter_headers(binned_profile_df)
                        if not parameter_dict:
                            print(colored(f"Parameter population failed for {cast_direction}; skipping.", 'red'))
                            continue

                        self._odf.parameter_headers = parameter_dict["parameter_headers"]
                        self._odf.data.parameter_list = parameter_dict["parameter_list"]
                        self._odf.data.print_formats = parameter_dict["print_formats"]
                        self._odf.data.data_frame = parameter_dict["data_frame"]

                        # HISTORY_HEADER (append one for this cast)
                        history_headers = []
                        history_header = HistoryHeader()
                        history_header.creation_date = datetime.now().strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
                        username = getpass.getuser()
                        history_header.add_process(f"RBR RSK file converted to ODF file by {username}")
                        history_headers.append(history_header)
                        self._odf.history_headers = history_headers

                        # Refresh ODF text buffer and write
                        self._odf.update_odf()

                        # Ensure filenames differ by direction, regardless of generate_file_spec() behavior
                        file_spec = self._odf.generate_file_spec()
                        self._odf.file_specification = file_spec
                        out_file = f"{file_spec}.ODF"

                        print(colored(f"Exporting {cast_direction} ODF: {out_file}", 'green'))
                        self._odf.write_odf(str(Path(odf_export_folder) / out_file), version=2.0)
            

    def _format_positional_value(self, position: float, position_type: str) -> str:
        degrees = int(position)
        minutes = abs(position - degrees) * 60
        degrees = abs(degrees)
        minutes = abs(minutes)
        if position_type == self.Position_Type.LAT.name:
            if position < 0:
                return f"S {degrees:02d} {minutes:.4f}"
            else:
                return f"N {degrees:02d} {minutes:.4f}"
        elif position_type == self.Position_Type.LON.name:
             if position < 0:
                return f"W {degrees:03d} {minutes:.4f}"
             else:
                return f"E {degrees:03d} {minutes:.4f}"


    def _export_btl(self):

        # Export .btl file
        msg = colored("Preparing to export to BTL ...", 'yellow')
        print(msg)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select the bottle id and depth file",
            "",
            "Text Files (*.txt);"
        )
        if file_path:
            print(f"Selected bottle id and depth file: {file_path}")
        else:
            print("No bottle id and depth file selected.")

        bottle_depths_df = pd.read_csv(file_path, header=None, names=["bottle_id", "depth"], skiprows=1)
        # print(bottle_depths_df)

        with RSK(self.rsk_file_path) as rsk:
            rsk.readdata()
            instrument_serial_number = str(rsk.instrument.serialID)

            rsk_df = pd.DataFrame(rsk.data)

        btl = BtlHeader(
            ship = self._odf.cruise_header.platform,
            cruise = self._odf.cruise_header.cruise_number,
            latitude = self._format_positional_value(self._odf.event_header.initial_latitude, "LAT"),
            longitude = self._format_positional_value(self._odf.event_header.initial_longitude, "LON"),
            sounding = self._odf.event_header.sounding,
            event_number = self._odf.event_header.event_number,
            cast = self._odf.event_header.event_qualifier1,
            station_name = self._odf.event_header.station_name,
            event_comments = '',
            instrument_serial_number = instrument_serial_number
        )

        # print(rsk_df.columns)
        
        print_widths = dict(
            Bottle=10,
            Bottle_SN=11,
            Date_Time=12,
            Parameter=16
        )

        # Filter dataframe to only the rows needed for BTL export
        data = rsk_df.copy()  # Avoid modifying the original DataFrame

        # Read seaodf.ini once for use in BTL file export
        seaodf = read_seaodf_parameters()
        odf_names = seaodf['odf_name'].to_list()
        odf_data_types = seaodf['data_type'].to_list()
        odf_precisions = seaodf['precision'].to_list()

        # Remove the parameter "specific_conductivity" if it exists, since it is not needed for the BTL export
        if "specific_conductivity" in data.columns:
            data = data.drop("specific_conductivity", axis=1)
        # Remove the parameter "pressure" if it exists, since it represents total atmospheric pressure and is not required for the BTL export
        if "pressure" in data.columns:
            data = data.drop("pressure", axis=1)

        print(data.head())

        param_dict = self._populate_parameter_headers(data.copy())
        params = param_dict["parameter_list"]
        # print(param_dict)

        dt_format = '%Y-%m-%d %H:%M:%S'
        dt_float_format = '%Y-%m-%d %H:%M:%S.%f'
        date_format = '%b %d %Y'
        time_format = '%H:%M:%S'

        btl_file = self._rsk_file.split(".")[0] + '.btl'

        if "dissolved_o2_concentration" in data.columns:       
            data['dissolved_o2_concentration'] = data['dissolved_o2_concentration'] / 44.66  # Convert from µmol/kg to ml/l

        with open(btl_file, 'w') as f:
            
            # Output the bottle header information at the top of the file
            print(btl)
            print(btl, file=f)

            avg_header = ''
            std_header = ''

            # Print header lines
            avg_header = f"{'Bottle':>{print_widths['Bottle']}}{'Bottle':>{print_widths['Bottle_SN']}}{'Date':>{print_widths['Date_Time']}}"
            std_header = f"{'Position':>{print_widths['Bottle']}}{'S/N':>{print_widths['Bottle_SN']}}{'Time':>{print_widths['Date_Time']}}"

            param_codes = list()
            for c, column in enumerate(data.columns.to_list()):
                toks = params[c].split("_")
                param_code = toks[0]
                if param_code == 'SYTM':
                    continue
                param_codes.append(param_code)
                param_num = int(toks[1]) - 1  # Extract the parameter number (e.g., 01 from TE90_01)
                y = odf_names.index(param_code) if param_code in odf_names else None
                if y is not None:
                    col_to_print = seaodf.iloc[y]['sbe_code']
                    if col_to_print == 'T090C':
                        col_to_print = f"T{param_num}90C"
                    if col_to_print == 'C0S/m':
                        col_to_print = f"C{param_num}S/m"
                    if col_to_print == 'Sal00':
                        col_to_print = f"Sal{param_num}{param_num}"
                    if col_to_print == 'DOXC' or col_to_print == 'DOXY':
                        col_to_print = f"Sbeox{param_num}ML/L"
                    avg_header += f"{col_to_print:>{print_widths['Parameter']}}"
            print(avg_header)
            print(std_header)
            print(avg_header, file=f)
            print(std_header, file=f)

            # Start outputting the means and standard deviations for each parameter at each bottle depth
            for pos, d in enumerate(bottle_depths_df["depth"].to_list(), start=1):
                dd = d - 1
                du = d + 1
                x = data[data["sea_pressure"].between(dd, du)]
                stats = x.agg(['mean', 'std'])
                print(stats.columns)

                avg_line = ''
                std_line = ''

                # Print the bottle number and ID for this depth
                avg_line += f"{pos:>{print_widths['Bottle']}}"
                bottle_id = str(bottle_depths_df.iloc[0]['bottle_id'])
                avg_line += f"{bottle_id:>{print_widths['Bottle_SN']}}"

                std_line += f"{'':>{print_widths['Bottle']}}"
                std_line += f"{'':>{print_widths['Bottle_SN']}}"

                # Extract the date and time strings for the current depth
                ts = str(stats['timestamp']['mean']).split(" ")
                tb = ts[1].split(":")
                seconds = float(tb[2])
                if seconds.is_integer():
                    bottle_dt = datetime.strptime(str(stats['timestamp']['mean']), dt_format)
                else:
                    bottle_dt = datetime.strptime(str(stats['timestamp']['mean']), dt_float_format)
                dstr = bottle_dt.strftime(date_format)
                tstr = bottle_dt.strftime(time_format)

                # Ouput the average (mean) line for the current depth
                avg_line += f"{dstr:>{print_widths['Date_Time']}}"
                data_columns = data.columns.to_list()
                param_codes = param_dict['parameter_list']
                for z, column in enumerate(data_columns):
                    param_code = param_codes[z][:4]
                    if param_code == 'SYTM':
                        continue
                    y = odf_names.index(param_code)
                    decimal_places = odf_precisions[y]
                    data_type = odf_data_types[y]
                    if data_type == "INTE":
                        avg_line += f"{stats[column]['mean']:>{print_widths['Parameter']}d}"
                    elif data_type == "DOUB":
                        avg_line += f"{stats[column]['mean']:>{print_widths['Parameter']}.{decimal_places}f}"
                    else:
                        avg_line += f"{stats[column]['mean']:>{print_widths['Parameter']}}"

                # Ouput the standard deviation (std) line for the current depth
                std_line += f"{tstr:>{print_widths['Date_Time']}}"
                stats = stats.iloc[:,1:]
                for z, column in enumerate(data_columns):
                    param_code = param_codes[z][:4]
                    if param_code == 'SYTM':
                        continue
                    y = odf_names.index(param_code)
                    decimal_places = odf_precisions[y]
                    if data_type == "INTE":
                        std_line += f"{stats[column]['std']:>{print_widths['Parameter']}d}"
                    elif data_type == "DOUB":
                        std_line += f"{stats[column]['std']:>{print_widths['Parameter']}.{decimal_places}f}"
                    else:
                        std_line += f"{stats[column]['std']:>{print_widths['Parameter']}}"

                print(avg_line)
                print(std_line)
                print(avg_line, file=f)
                print(std_line, file=f)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
