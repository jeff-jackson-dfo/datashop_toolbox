from odf_toolbox import OdfHeader
from odf_oracle.sytm_to_timestamp import sytm_to_timestamp
from odf_oracle.fix_null import fix_null

def cruise_event_to_oracle(odfobj: OdfHeader, connection, infile: str) -> str:
    """
    Load the ODF object's cruise header and event header metadata into Oracle.
    
    Parameters
    ----------
    odfobj: OdfHeader class object
        The ODF object to be loaded into Oracle.
    connection: oracledb connection
        Oracle database connection object.
    infile: str
        Name of ODF file currently being loaded into the database.

    Returns
    -------
    odf_file: str
        The file name of the ODF object that was loaded into the database.
    """

    # Check the Country Institute Code.
    country_institute_code = \
        str(odfobj.cruise_header.country_institute_code)
    if len(country_institute_code) != 4:
        country_institute_code = '1810'

    # Create a cursor to the open connection.
    with connection.cursor() as cursor:

        # Check to see if the current ODF file is from a groundfish (AZMP Ecosystem
        # Trawl Survey). If it is then do not create the ODF filename to be stored 
        # in the database from the ODF metadata but instead use the input filename.
        cruise_description = odfobj.cruise_header.cruise_description
        set_number = '0'
        if 'TRAWL' in cruise_description.upper():
            # Drop the extension.
            odf_filename = infile[0:-4]
            # Get the set number from the file name.
            items = odf_filename.split('_', 3)
            set_number = items[2]
            # if set_number != odfobj.event_header.get_set_number():
            #     odfobj.event_header.set_set_number(set_number)
        else:
            odf_filename = odfobj.file_specification.strip("'")
            print(f'odf_filename: {odf_filename}')
            # Make the set number 0 for non-trawl surveys.
            odfobj.event_header.set_number = set_number

        # ic(sytm_to_timestamp(odfobj.cruise_header.get_start_date(), 'date'))
        # ic(sytm_to_timestamp(odfobj.event_header.get_start_date_time(), 'datetime'))

        # Execute the Insert SQL statement.
        cursor.execute(
            "INSERT INTO ODF_CRUISE_EVENT (COUNTRY_CODE, INSTITUTE_CODE, "
            "CRUISE_NUMBER, ORGANIZATION, CHIEF_SCIENTIST, START_DATE, END_DATE, "
            "PLATFORM, AREA_OF_OPERATION, CRUISE_DESCRIPTION, DATA_TYPE, "
            "EVENT_NUMBER, EVENT_QUALIFIER1, EVENT_QUALIFIER2, CREATION_DATE, "
            "ORIG_CREATION_DATE, START_DATE_TIME, END_DATE_TIME, INITIAL_LATITUDE, "
            "INITIAL_LONGITUDE, END_LATITUDE, END_LONGITUDE, MIN_DEPTH, MAX_DEPTH, "
            "SAMPLING_INTERVAL, SOUNDING, DEPTH_OFF_BOTTOM, STATION_NAME, "
            "SET_NUMBER, RESEARCH_PROGRAM, DATA_ACCESS_LEVEL, ODF_FILENAME) "
            "VALUES (:ccode, :icode, :cnum, :org, :cs, "
            # "TO_DATE(:sdate, \'YYYY-MM-DD\'), TO_DATE(:edate, \'YYYY-MM-DD\'), "
            ":sdate, :edate, "
            ":plat, :aop, :cdes, :dt, :enum, :eq1, :eq2, "
            # "TO_TIMESTAMP(:cdate, \'YYYY-MM-DD HH24:MI:SS.FF\'), "
            # "TO_TIMESTAMP(:odate, \'YYYY-MM-DD HH24:MI:SS.FF\'), "
            # "TO_TIMESTAMP(:sdt, \'YYYY-MM-DD HH24:MI:SS.FF\'), "
            # "TO_TIMESTAMP(:edt, \'YYYY-MM-DD HH24:MI:SS.FF\'), :ilat, :ilon, "
            ":cdate, :odate, :sdt, :edt, :ilat, :ilon, "
            ":elat, :elon, :mind, :maxd, :sint, :snd, "
            ":dob, :stn, :setnum, :resprg, :dflag, :fname)",
            {
                'ccode': int(country_institute_code[0:2]),
                'icode': int(country_institute_code[2:4]),
                'cnum': odfobj.cruise_header.cruise_number,
                'org': odfobj.cruise_header.organization,
                'cs': odfobj.cruise_header.chief_scientist,
                'sdate': sytm_to_timestamp(
                    odfobj.cruise_header.start_date, 'date'),
                'edate': sytm_to_timestamp(
                    odfobj.cruise_header.end_date, 'date'),
                'plat': odfobj.cruise_header.platform,
                'aop': odfobj.cruise_header.area_of_operation,
                'cdes': odfobj.cruise_header.cruise_description,
                'dt': odfobj.event_header.data_type,
                'enum': odfobj.event_header.event_number,
                'eq1': odfobj.event_header.event_qualifier1,
                'eq2': odfobj.event_header.event_qualifier2,
                'cdate': sytm_to_timestamp(
                    odfobj.event_header.creation_date, 'datetime'),
                'odate': sytm_to_timestamp(
                    odfobj.event_header.orig_creation_date, 'datetime'),
                'sdt': sytm_to_timestamp(
                    odfobj.event_header.start_date_time, 'datetime'),
                'edt': sytm_to_timestamp(
                    odfobj.event_header.end_date_time, 'datetime'),
                'ilat': fix_null(float(odfobj.event_header.initial_latitude)),
                'ilon': fix_null(float(
                    odfobj.event_header.initial_longitude)),
                'elat': fix_null(float(odfobj.event_header.end_latitude)),
                'elon': fix_null(float(odfobj.event_header.end_longitude)),
                'mind': fix_null(float(odfobj.event_header.min_depth)),
                'maxd': fix_null(float(odfobj.event_header.max_depth)),
                'sint': fix_null(float(
                    odfobj.event_header.sampling_interval)),
                'snd': fix_null(float(odfobj.event_header.sounding)),
                'dob': fix_null(float(odfobj.event_header.depth_off_bottom)),
                'stn': odfobj.event_header.station_name,
                'setnum': set_number,
                'resprg': '',
                'dflag': '',
                'fname': odf_filename
            }
            )

        # Commit the changes to the database.
        connection.commit()

        print('\nCruise_Header and Event_Header successfully loaded into Oracle.')

    return odf_filename
