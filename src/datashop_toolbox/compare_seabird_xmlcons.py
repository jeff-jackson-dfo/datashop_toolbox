import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd


def parse_xmlcon(filename: str) -> pd.DataFrame:
    """Parse a Sea-Bird .xmlcon file into a sensor DataFrame.

    Args:
        filename: Path to the ``.xmlcon`` file to parse. The event
            number is taken from characters 4:7 of the filename.

    Returns:
        A DataFrame with one row per sensor, and columns ``Event``,
        ``Sensor``, ``Index``, ``SensorID``, and ``SerialNumber``.
        Returns ``None`` if the file cannot be parsed as XML.
    """
    # df = pd.DataFrame(columns = ['Event', 'Sensor', 'Index', 'SensorID', 'SerialNumber', 'CalibrationDate'])
    df = pd.DataFrame(columns=["Event", "Sensor", "Index", "SensorID", "SerialNumber"])
    try:
        # print(f"Parsing XML file: {filename}")
        tree = ET.parse(filename)
        # root element should be 'SBE_InstrumentConfiguration'
        root = tree.getroot()
        event = int(filename[4:7])
        # Iterate through the 'SensorArray' child elements to find sensor ids
        for sensor in root.findall(".//SensorArray/Sensor"):
            sensor_id = sensor.get("SensorID")
            for child in sensor[0]:
                if child.tag == "SerialNumber":
                    serial_number = child.text
                # if child.tag == 'CalibrationDate':
                #     calibration_date = child.text
            # Add the data to the DataFrame
            new_row = pd.DataFrame(
                [
                    {
                        "Event": event,
                        "Sensor": sensor[0].tag,
                        "Index": int(sensor.get("index")),
                        "SensorID": int(sensor_id),
                        "SerialNumber": serial_number,
                    }
                ]
            )
            # 'CalibrationDate': calibration_date}])
            df = pd.concat([df, new_row], ignore_index=True)
    except ET.ParseError as e:
        print(f"Error parsing XML file {filename}: {e}")
        return None
    return df


def compare_xmlcons(df: pd.DataFrame) -> pd.DataFrame:
    """Find rows where a sensor's serial number changes between events.

    Args:
        df: Combined sensor DataFrame, as produced by
            :func:`parse_xmlcon`, with one row per sensor per event.

    Returns:
        The subset of rows, for each sensor ``Index``, where
        ``SerialNumber`` differs from the immediately preceding row
        (in file order) for that index — i.e. the events at which a
        sensor was swapped.
    """
    indices = df["Index"].unique()
    df_sensor_changes = pd.DataFrame(
        columns=["Event", "Sensor", "Index", "SensorID", "SerialNumber"]
    )
    for idx in indices:
        filtered_df = df[df["Index"] == idx]
        # Find rows where 'SerialNumber' column changes
        # Create a boolean Series indicating where the 'SerialNumber' value differs from the previous row
        category_changes = filtered_df["SerialNumber"].ne(filtered_df["SerialNumber"].shift())
        rows_with_category_changes = filtered_df[category_changes]
        # print(rows_with_category_changes)
        df_sensor_changes = pd.concat(
            [df_sensor_changes, rows_with_category_changes], ignore_index=True
        )
    return df_sensor_changes


def transform_to_wide_format(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot a long-format sensor-change table to wide format.

    Args:
        df: Long-format DataFrame with ``Event``, ``SensorName``, and
            ``SerialNumber`` columns.

    Returns:
        A DataFrame indexed by ``Event`` with one column per
        ``SensorName``, holding the corresponding ``SerialNumber``.
    """
    # Pivot the DataFrame to wide format
    df_wide = df.pivot(index="Event", columns="SensorName", values="SerialNumber")
    return df_wide


def main():

    # Set options to display all rows and columns
    pd.set_option("display.max_rows", None)  # Display all rows
    pd.set_option("display.max_columns", None)  # Display all columns
    pd.set_option("display.width", None)  # Adjust display width for better readability (optional)
    pd.set_option("display.max_colwidth", None)  # Display full content of columns (optional)

    # Change to the drive's root folder
    os.chdir("\\")
    drive = Path.cwd()

    # pathlist = ['DEV', 'Data', '2025', 'LAT2025146', 'CTD', \
    # 'DATASHOP_PROCESSING', 'Step_2_Apply_Calibrations', 'ctddata']
    pathlist = ["DEV", "GitHub", "datashop_toolbox", "tests"]

    # Generate the top folder path
    top_folder = Path.joinpath(drive, *pathlist)

    path_to_orig = Path.joinpath(top_folder, "XMLCON")

    # Change to folder containing files to be modified
    os.chdir(path_to_orig)

    # Find all ODF files in the current directory.
    files = Path.glob("*.xmlcon")

    df_sensors = pd.DataFrame(columns=["Event", "Sensor", "Index", "SensorID", "SerialNumber"])
    # df_sensors = pd.DataFrame(columns=['Event', 'Sensor', 'Index', 'SensorID', 'SerialNumber', 'CalibrationDate'])

    # Loop through the list of XMLCON files.
    for _x, file_name in enumerate(files):
        # if x == 0:
        my_df = parse_xmlcon(file_name)
        df_sensors = pd.concat([df_sensors, my_df], ignore_index=True)

    # Compare the XMLCON files.
    df_sensor_changes = compare_xmlcons(df_sensors)
    df_sensor_changes = df_sensor_changes.sort_values(by=["Event", "Index"]).reset_index(drop=True)
    df_sensor_changes.to_excel("LAT2025146_CTD_Sensor_Changes.xlsx", index=False)

    # Transform the DataFrame to wide format
    df_sensor_changes["SensorName"] = (
        df_sensor_changes["Sensor"] + "_" + df_sensor_changes["Index"].astype(str)
    )
    df_sensor_changes_condensed = df_sensor_changes[["Event", "SensorName", "SerialNumber"]]
    df_wide = transform_to_wide_format(df_sensor_changes_condensed)
    df_wide.to_excel("LAT2025146_CTD_Sensor_Changes_Wide.xlsx", index=True)


if __name__ == "__main__":
    main()
