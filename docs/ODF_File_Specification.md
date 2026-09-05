# ODF Format Specification


author : Jeff Jackson

Created: 03-JAN-2024

Last updated: 06-AUG-2024

version : 3.0

© 2024, Fisheries and Oceans Canada (DFO).

The Oceans Data Format (ODF) is an ASCII text file format used for the
primary storage of an oceanographic data series. It consists of a set of
header blocks that contain the metadata followed by rows of data
records.

## Introduction

The following document presents the details of the ODF file format
specification.

## ODF Version 3.0

This specification details both the ODF Header section and the ODF Data
section.

The specification underwent a major revision for this version.

The major reasons for this were:

- to improve its usefulness by making the data easier to read into other
  software systems, and
- to clean up the format by removing information that was of no use and
  adding important information that was missing.

This major revision coincides with the development of a new ODF toolbox
using the Python programming language.

## ODF Header Section

### Indents, Commas, Capitalisation and Strings

It is common to have indents on field lines (normally two spaces) but
this is not a strict requirement. However, indents are recommended
because they increase human readability.

Header lines will no longer have a trailing comma.

Uppercase block and field names are mandatory in the ODF format
specification.

All values in string fields are enclosed by single quotes.

### Date/Time Fields in the Header Blocks

Date/Time information is stored as a text string in this specification.
The format of the system had its beginnings in the CMSYS system in the
mid-1980s. The format, was referred to as SYstem TiMe or SYTM, and
represents Date/Time values in the following way:

dd-MMM-yyyy hh:mm:ss.ss

where there is a single space exists between the date and time, and the
seconds are displayed to the nearest hundredth.

Examples would be:

> 14-JUN-1999 14:47:40.37
>
> 02-SEP-1997 01:08:06.67

This field always consists of 23 characters.

> [!NOTE]
>
> The SYTM null value is: 17-NOV-1858 00:00:00.00.
>
> This value was chosen because it corresponded to time = 0 on the
> original ODF computing platform (VAX / VMS).
>
> Once placed into a field, the value carries forward as a valid date.

### ODF_HEADER Block (mandatory)

| Block Name | Field Name                | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value | Null Value |
|------------|---------------------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:----------:|
| ODF_HEADER | FILE_SPECIFICATION        |         n         | string |         n         |           1           |     empty     |    none    |
| ODF_HEADER | ODF_SPECIFICATION_VERSION |         n         | string |         y         |           1           |      3.0      |    none    |

Table 1 - ODF_HEADER block details

<br/>

The ODF_HEADER block is mandatory.

All fields in the ODF_HEADER block are mandatory.

An empty string is the default null value for the FILE_SPECIFICATION
field.

Normally this field contains the standard ODF file name without the
extension.

Where the standard ODF file name is a concatenation of the following
list of strings separated by underscores: - EVENT_HEADER.DATA_TYPE
(e.g. ‘CTD’) - CRUISE_HEADER.CRUISE_NUMBER (e.g. ‘CAR2023011’) -
EVENT_HEADER.EVENT_NUMBER (e.g. ‘017’) - EVENT_HEADER.EVENT_QUALIFIER1
(e.g. ‘496844’) - EVENT_HEADER.EVENT_QUALIFIER2 (e.g. ‘DN’)

The ODF_HEADER block is the first block presented in an ODF file.

An example of an ODF_HEADER block follows:

<pre>
ODF_HEADER
  FILE_SPECIFICATION = 'CTD_CAR2023011_017_496844_DN'
  ODF_SPECIFICATION_VERSION = 3.0
</pre>
<br/>

### CRUISE_HEADER Block (mandatory)

| Block Name    | Field Name             | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value |       Null Value        |
|---------------|------------------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:-----------------------:|
| CRUISE_HEADER | COUNTRY_INSTITUTE_CODE |         n         | number |         n         |           1           |     empty     |          none           |
| CRUISE_HEADER | CRUISE_NUMBER          |         n         | string |         n         |           1           |     empty     |          none           |
| CRUISE_HEADER | ORGANIZATION           |         n         | string |         n         |           1           |     empty     |          none           |
| CRUISE_HEADER | CHIEF_SCIENTIST        |         n         | string |         n         |           1           |     empty     |          none           |
| CRUISE_HEADER | START_DATE             |         n         |  SYTM  |         n         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| CRUISE_HEADER | END_DATE               |         n         |  SYTM  |         n         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| CRUISE_HEADER | PLATFORM               |         n         | string |         n         |           1           |     empty     |          none           |
| CRUISE_HEADER | AREA_OF_OPERATION      |         n         | string |         n         |           1           |     empty     |          none           |
| CRUISE_HEADER | CRUISE_NAME            |         n         | string |         n         |           1           |     empty     |          none           |
| CRUISE_HEADER | CRUISE_DESCRIPTION     |         n         | string |         n         |           1           |     empty     |          none           |

Table 2 - CRUISE_HEADER block details

<br/>

The CRUISE_HEADER block consists of metadata that relates to the entire
mission.

The CRUISE_HEADER block is mandatory.

All fields in the CRUISE_HEADER block are mandatory.

The fields are also order dependent and must conform to the above order.

Only COUNTRY_INSTITUTE_CODE is a number while all other fields are
strings.

There is no requirement for trailing spaces in any of the field strings.

If a string field is empty, then only two successive single quotes are
required.

The START_DATE and END_DATE fields are given in SYTM format.

The CRUISE_HEADER block follows the ODF_HEADER block.

An example CRUISE_HEADER block follows:

<pre>
CRUISE_HEADER
  COUNTRY_INSTITUTE_CODE = 1810
  CRUISE_NUMBER = '96006'
  ORGANIZATION = 'PCS BIO'
  CHIEF_SCIENTIST = ''
  START_DATE = '17-NOV-1858 00:00:00.00'
  END_DATE = '17-NOV-1858 00:00:00.00'
  PLATFORM = 'CSS Hudson'
  AREA_OF_OPERATION = 'SCOTIAN SLOPE'
  CRUISE_NAME = 'WOCE LABRADOR SEA'
  CRUISE_DESCRIPTION = 'WOCE AR7W LABRADOR SEA'
</pre>
<br/>

### EVENT_HEADER Block (mandatory)

| Block Name   | Field Name         | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value |       Null Value        |
|--------------|--------------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:-----------------------:|
| EVENT_HEADER | DATA_TYPE          |         n         | string |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | EVENT_NUMBER       |         n         | string |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | EVENT_QUALIFIER1   |         n         | string |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | EVENT_QUALIFIER2   |         n         | string |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | CREATION_DATE      |         n         |  SYTM  |         n         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| EVENT_HEADER | ORIG_CREATION_DATE |         n         |  SYTM  |         n         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| EVENT_HEADER | START_DATE_TIME    |         n         |  SYTM  |         n         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| EVENT_HEADER | END_DATE_TIME      |         n         |  SYTM  |         n         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| EVENT_HEADER | INITIAL_LATITUDE   |         n         | number |         n         |           1           |     empty     |           -99           |
| EVENT_HEADER | INITIAL_LONGITUDE  |         n         | number |         n         |           1           |     empty     |          -999           |
| EVENT_HEADER | END_LATITUDE       |         n         | number |         n         |           1           |     empty     |           -99           |
| EVENT_HEADER | END_LONGITUDE      |         n         | number |         n         |           1           |     empty     |          -999           |
| EVENT_HEADER | MIN_DEPTH          |         n         | number |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | MAX_DEPTH          |         n         | number |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | SAMPLING_INTERVAL  |         n         | number |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | SOUNDING           |         n         | number |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | DEPTH_OFF_BOTTOM   |         n         | number |         n         |           1           |     empty     |          none           |
| EVENT_HEADER | EVENT_COMMENTS     |         n         | string |         n         |          1+           |     empty     |          none           |

Table 3 - EVENT_HEADER block details

<br/>

The EVENT_HEADER block consists of metadata related to a specific event
that occurred during the mission.

The EVENT_HEADER block is mandatory.

All fields in the EVENT_HEADER block are mandatory.

The fields are also order dependent and must conform to the above order.

Multiple EVENT_COMMENTS are permitted within the EVENT_HEADER block.

All other fields have a single occurrence.

The EVENT_HEADER block follows the CRUISE_HEADER block.

An example EVENT_HEADER block follows:

<pre>
EVENT_HEADER
  DATA_TYPE = 'CTD'
  EVENT_NUMBER = '012'
  EVENT_QUALIFIER1 = '1'
  EVENT_QUALIFIER2 = 'DN'
  CREATION_DATE = '04-JUN-1999 14:47:40.34'
  ORIG_CREATION_DATE = '26-JUN-1996 18:15:25.05'
  START_DATE_TIME = '15-MAY-1996 05:50:15.00'
  END_DATE_TIME = '17-NOV-1858 00:00:00.00'
  INITIAL_LATITUDE = 43.7823
  INITIAL_LONGITUDE = -57.8332
  END_LATITUDE = -99.0000
  END_LONGITUDE = -999.0000
  MIN_DEPTH = 1.0
  MAX_DEPTH = 205.0
  SAMPLING_INTERVAL = 0.0000
  SOUNDING = 2450.0
  DEPTH_OFF_BOTTOM = 2245.0
  EVENT_COMMENTS = ''
  EVENT_COMMENTS = '04-JUN-1999 14:47:40.00 - NOTE THERE IS BAD DATA FROM SURFACE TO 10 DBARS'
</pre>

> [!WARNING]
>
> Sampling_Interval must always be in seconds.

<br/>

### METEO_HEADER Block (mandatory)

| Block Name   | Field Name           | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value | Null Value |
|--------------|----------------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:----------:|
| METEO_HEADER | AIR_TEMPERATURE      |         n         | number |         n         |           1           |     empty     |    none    |
| METEO_HEADER | ATMOSPHERIC_PRESSURE |         n         | number |         n         |           1           |     empty     |    none    |
| METEO_HEADER | WIND_SPEED           |         n         | number |         n         |           1           |     empty     |    none    |
| METEO_HEADER | WIND_DIRECTION       |         n         | number |         n         |           1           |     empty     |    none    |
| METEO_HEADER | SEA_STATE            |         n         | number |         n         |           1           |     empty     |    none    |
| METEO_HEADER | CLOUD_COVER          |         n         | number |         n         |           1           |     empty     |    none    |
| METEO_HEADER | ICE_THICKNESS        |         n         | number |         n         |           1           |     empty     |    none    |
| METEO_HEADER | METEO_COMMENTS       |         n         | string |         n         |          1…n          |     empty     |    none    |

Table 4 - METEO_HEADER block details

<br/>

The METEO_HEADER block consists of metadata that relates to
meteorological data obtained during the mission’s event.

The METEO_HEADER block is not mandatory.

All fields in the METEO_HEADER block are mandatory when the block is
present.

The fields are also order dependent and must conform to the above order.

If a string field is empty, then only two successive single quotes are
required.

The METEO_HEADER block follows the EVENT_HEADER block.

An example METEO_HEADER block follows:

<pre>
METEO_HEADER,
  AIR_TEMPERATURE = -99.00,
  ATMOSPHERIC_PRESSURE = -99.00,
  WIND_SPEED = 4.60,
  WIND_DIRECTION = 135.00,
  SEA_STATE = 3,
  CLOUD_COVER = 8,
  ICE_THICKNESS = 0.000,
  METEO_COMMENTS = ''
</pre>
<br/>

### INSTRUMENT_HEADER Block (mandatory)

| Block Name        | Field Name    | RestrictedValues |  Type  | Content Mandatory | Number of Occurrences | Default Value | Null Value |
|-------------------|---------------|:----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:----------:|
| INSTRUMENT_HEADER | INST_TYPE     |        n         | string |         n         |           1           |     empty     |    none    |
| INSTRUMENT_HEADER | MODEL         |        n         | string |         n         |           1           |     empty     |    none    |
| INSTRUMENT_HEADER | SERIAL_NUMBER |        n         | string |         n         |           1           |     empty     |    none    |
| INSTRUMENT_HEADER | DESCRIPTION   |        n         | string |         n         |           1           |     empty     |    none    |

Table 5 - INSTRUMENT_HEADER block details

<br/>

The INSTRUMENT_HEADER block consists of metadata describing the
instrument used to acquire the data in the file.

The INSTRUMENT_HEADER block is mandatory.

All fields in the INSTRUMENT_HEADER block are mandatory.

The fields are also order dependent and must conform to the above order.

The INSTRUMENT_HEADER block follows the METEO_HEADER block (if present)
otherwise the EVENT_HEADER block.

An example of the INSTRUMENT_HEADER block follows:

<pre>
INSTRUMENT_HEADER
  INST_TYPE = 'Sea-Bird'
  MODEL = 'SBE 9' 
  SERIAL_NUMBER = '9P 7356-299'
  DESCRIPTION = '006A012.DAT 006A012.CON'
</pre>
<br/>

### QUALITY_HEADER Block (mandatory)

| Block Name     | Field Name       | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value |       Null Value        |
|----------------|------------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:-----------------------:|
| QUALITY_HEADER | QUALITY_DATE     |         n         |  SYTM  |         y         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| QUALITY_HEADER | QUALITY_TESTS    |         n         | string |         y         |           1           |     empty     |          none           |
| QUALITY_HEADER | QUALITY_COMMENTS |         n         | string |         y         |          1…n          |     empty     |          none           |

Table 6 - QUALITY_HEADER block details

<br/>

The QUALITY_HEADER block consists of metadata that relates to the file’s
data quality.

The QUALITY_HEADER block is not mandatory.

All fields in the QUALITY_HEADER block are mandatory when the block is
present.

The fields are also order dependent and must conform to the above order.

If a string field is empty, then only two successive single quotes are
required.

The QUALITY_DATE field is given in SYTM format.

The QUALITY_HEADER block follows the INSTRUMENT_HEADER block.

An example QUALITY_HEADER block follows:

<pre>
QUALITY_HEADER
  QUALITY_DATE='29-NOV-2023 14:34:11.02',
  QUALITY_TESTS='QUALITY CONTROL TESTS RUN',
  QUALITY_TESTS='Test 2.1: GTSPP Global Impossible Parameter Values (4)',
  QUALITY_TESTS='Test 2.2: GTSPP Regional Impossible Parameter Values (8)',
  QUALITY_TESTS='Test 2.3: GTSPP Increasing Depth (16)',
  QUALITY_TESTS='Test 2.4: GTSPP Profile Envelope (Temperature and Salinity) (32)',
  QUALITY_TESTS='Test 2.5: GTSPP Constant Profile (64)',
  QUALITY_TESTS='Test 2.6: GTSPP Freezing Point (128)',
  QUALITY_TESTS='Test 2.7: GTSPP Spike in Temperature and Salinity (one point) (256)',
  QUALITY_TESTS='Test 2.8: GTSPP Top and Bottom Spike in Temperature and Salinity (512)',
  QUALITY_TESTS='Test 2.9: GTSPP Gradient in Temperature and Salinity (1024)',
  QUALITY_TESTS='Test 2.10: GTSPP Density Inversion (point to point) (2048)',
  QUALITY_TESTS='Test 2.11: IML Spike in Pressure, Temperature and Salinity (one point or more) (4096)',
  QUALITY_TESTS='Test 2.12: IML Density Inversion (overall profile) (8192)'
  QUALITY_COMMENTS='QUALITY CODES',
  QUALITY_COMMENTS='0: Value has not been quality controlled',
  QUALITY_COMMENTS='1: Value seems to be correct',
  QUALITY_COMMENTS='2: Value appears inconsistent with other values',
  QUALITY_COMMENTS='3: Value seems doubtful',
  QUALITY_COMMENTS='4: Value seems erroneous',
  QUALITY_COMMENTS='5: Value was modified',
  QUALITY_COMMENTS='9: Value is missing',
  QUALITY_COMMENTS='QCFF CHANNEL',
  QUALITY_COMMENTS='The QCFF flag allows one to determine from which test(s) the quality flag(s) originate',
  QUALITY_COMMENTS='It only applies to the stage 2 quality control tests.',
  QUALITY_COMMENTS='Each test in this step is associated with a number 2x, where x is a whole positive number.',
  QUALITY_COMMENTS='Before running the quality control, a QCFF value of 0 is attributed to each line of data.',
  QUALITY_COMMENTS='When a test fails, the value of 2x that is associated with that test is added to the QCFF.',
  QUALITY_COMMENTS='In this way one can easily identify which tests failed by analyzing the QCFF value.',
  QUALITY_COMMENTS='If the QC flag of a record is modified by hand, a value of 1 is added to the QCFF.',
  QUALITY_COMMENTS='QUALITY CONTROL TEST RESULTS',
  QUALITY_COMMENTS='Test 2.1 Global Impossible Parameter Values -> ok',
  QUALITY_COMMENTS='Test 2.2 Regional Impossible Parameter Values -> ok',
  QUALITY_COMMENTS='Test 2.3 Increasing Depth -> ok',
  QUALITY_COMMENTS='Test 2.4 Profile Envelope -> ok',
  QUALITY_COMMENTS='Test 2.5 Constant Profile -> ok',
  QUALITY_COMMENTS='Test 2.6 Freezing Point -> ok',
  QUALITY_COMMENTS='Test 2.7 Spike in Temperature and Salinity (one point) -> ok',
  QUALITY_COMMENTS='Test 2.8 Top and Bottom Spike in Temperature and Salinity (one point) -> ok',
  QUALITY_COMMENTS='Test 2.9 Gradient (point to point) -> ok',
  QUALITY_COMMENTS='Test 2.10 Density Inversion (point to point) -> Density inversion found (SIGP_01)',
  QUALITY_COMMENTS='Test 2.11 Spike (one point or more) (supplementary test) -> ok',
  QUALITY_COMMENTS='Test 2.12 Density Inversion (overall profile) -> Density inversion found (SIGP_01)'
</pre>
<br/>

### POLYNOMIAL_CAL_HEADER Block (optional)

| Block Name            | Field Name             | Restricted Values |   Type    | Content Mandatory | Number of Occurrences | Default Value |       Null Value        |
|-----------------------|------------------------|:-----------------:|:---------:|:-----------------:|:---------------------:|:-------------:|:-----------------------:|
| POLYNOMIAL_CAL_HEADER | PARAMETER_CODE         |         y         |  string   |         y         |           1           |     empty     |          none           |
| POLYNOMIAL_CAL_HEADER | CALIBRATION_DATE       |         n         |   SYTM    |         y         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| POLYNOMIAL_CAL_HEADER | APPLICATION_DATE       |         n         |   SYTM    |         y         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| POLYNOMIAL_CAL_HEADER | NUMBER_OF_COEFFICIENTS |         n         |  number   |         y         |           1           |     empty     |          none           |
| POLYNOMIAL_CAL_HEADER | COEFFICIENTS           |         n         | number(s) |         y         |          1…n          |     empty     |          none           |

Table 7 - POLYNOMIAL_CAL_HEADER block details

<br/>

The POLYNOMIAL_CAL_HEADER block consists of metadata describing a
polynomial calibration applied to a parameter in the file.

The POLYNOMIAL_CAL_HEADER block is not mandatory.

All fields in the POLYNOMIAL_CAL_HEADER block are mandatory when the
block is present.

The fields are also order dependent and must conform to the above order.

The NUMBER_COEFFICIENTS value must correspond to the actual number of
coefficients listed in the block.

The POLYNOMIAL_CAL_HEADER block(s) must precede the HISTORY_HEADER
block(s).

An example POLYNOMIAL_CAL_HEADER block follows:

<pre>
 POLYNOMIAL_CAL_HEADER
  PARAMETER_CODE = 'PSAL_02'
  CALIBRATION_DATE = '11-SEP-1996 14:51:25.74'
  APPLICATION_DATE = '11-SEP-1996 14:51:25.74'
  NUMBER_COEFFICIENTS = 2
  COEFFICIENTS = -.31800001D-03 0.10000000D+01
</pre>
<br/>

### GENERAL_CAL_HEADER Block (optional)

| Block Name         | Field Name             | Restricted Values |   Type    | Content Mandatory | Number of Occurrences | Default Value |       Null Value        |
|--------------------|------------------------|:-----------------:|:---------:|:-----------------:|:---------------------:|:-------------:|:-----------------------:|
| GENERAL_CAL_HEADER | PARAMETER_CODE         |         y         |  string   |         y         |           1           |     empty     |          none           |
| GENERAL_CAL_HEADER | CALIBRATION_TYPE       |         n         |  string   |         y         |           1           |     empty     |          none           |
| GENERAL_CAL_HEADER | CALIBRATION_DATE       |         n         |   SYTM    |         y         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| GENERAL_CAL_HEADER | APPLICATION_DATE       |         n         |   SYTM    |         y         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| GENERAL_CAL_HEADER | NUMBER_OF_COEFFICIENTS |         n         |  number   |         y         |           1           |     empty     |          none           |
| GENERAL_CAL_HEADER | COEFFICIENTS           |         n         | number(s) |         y         |          1…n          |     empty     |          none           |
| GENERAL_CAL_HEADER | CALIBRATION_EQUATION   |         n         |  string   |         y         |           1           |     empty     |          none           |
| GENERAL_CAL_HEADER | CALIBRATION_COMMENTS   |         n         |  string   |         y         |          1…n          |     empty     |          none           |

Table 8 - GENERAL_CAL_HEADER block details

<br/>

The GENERAL_CAL_HEADER block consists of metadata describing a general
calibration applied to a parameter in the file.

The GENERAL_CAL_HEADER block is not mandatory.

All fields in the GENERAL_CAL_HEADER block are mandatory when the block
is present.

The fields are also order dependent and must conform to the above order.

The NUMBER_COEFFICIENTS value must correspond to the actual number of
coefficients listed in the block.

The GENERAL_CAL_HEADER block(s) must precede the HISTORY_HEADER
block(s).

An example GENERAL_CAL_HEADER block follows:

<pre>
 GENERAL_CAL_HEADER
  PARAMETER_CODE = 'PRES_01',
  CALIBRATION_TYPE = 'PRES04',
  CALIBRATION_DATE = '04-NOV-1997 00:00:00.00',
  APPLICATION_DATE = '23-AUG-2000 11:56:23.00',
  NUMBER_OF_COEFFICIENTS = 4,
  COEFFICIENTS = -3.97110200e-02 -7.14514600e+03 0.00000000e+00 0.00000000e+00 ,
  CALIBRATION_EQUATION = 'PRES = (C0 + C1*N + C2*N^2 + C3)/1.450377',
  CALIBRATION_COMMENTS = '',
</pre>
<br/>

### COMPASS_CAL_HEADER Block (optional)

| Block Name         | Field Name       | Restricted Values |   Type    | Content Mandatory | Number of Occurrences | Default Value | Null Value |
|--------------------|------------------|:-----------------:|:---------:|:-----------------:|:---------------------:|:-------------:|:----------:|
| COMPASS_CAL_HEADER | PARAMETER_CODE   |         n         |  string   |         y         |           1           |     empty     |    none    |
| COMPASS_CAL_HEADER | CALIBRATION_DATE |         n         |   SYTM    |         y         |           1           |     empty     |    none    |
| COMPASS_CAL_HEADER | APPLICATION_DATE |         n         |   SYTM    |         y         |           1           |     empty     |    none    |
| COMPASS_CAL_HEADER | DIRECTIONS       |         y         | number(s) |         y         |          1…n          |     empty     |    none    |
| COMPASS_CAL_HEADER | CORRECTIONS      |         y         | number(s) |         y         |          1…n          |     empty     |    none    |

Table 9 - COMPASS_CAL_HEADER block details

<br/>

The COMPASS_CAL_HEADER block consists of metadata describing a
calibration applied to the current meter data in the file.

The COMPASS_CAL_HEADER block is not mandatory.

All fields in the COMPASS_CAL_HEADER block are mandatory when the block
is present.

The fields are also order dependent and must conform to the above order.

Multiple COMPASS_CAL_HEADER blocks can exist in one ODF file.

The COMPASS_CAL_HEADER block(s) must precede the HISTORY_HEADER
block(s).

<pre>
COMPASS_CAL_HEADER,
  PARAMETER_NAME='HCDT_01',
  CALIBRATION_DATE='26-JUL-2011 10:43:10.19',
  APPLICATION_DATE='26-JUL-2011 10:43:10.19',
  DIRECTIONS=8.30000000E+000  1.83000000E+001  2.83000000E+001  3.83000000E+001  4.83000000E+001  5.83000000E+001  6.83000000E+001  7.83000000E+001  8.83000000E+001  9.83000000E+001  1.08300000E+002  1.18300000E+002  1.28300000E+002  1.38300000E+002  1.48300000E+002  1.58300000E+002  1.68300000E+002  1.78300000E+002  1.88300000E+002  1.98300000E+002  2.08300000E+002  2.18300000E+002  2.28300000E+002  2.38300000E+002  2.48300000E+002  2.58300000E+002  2.68300000E+002  2.78300000E+002  2.88300000E+002  2.98300000E+002  3.08300000E+002  3.18300000E+002  3.28300000E+002  3.38300000E+002  3.48300000E+002  3.58300000E+002,
  CORRECTIONS=1.40000000E+000  1.20000000E+000  9.00000000E-001  2.00000000E-001  8.00000000E-001  1.00000000E+000  8.00000000E-001  8.00000000E-001  3.00000000E-001  0.00000000E+000  0.00000000E+000  -5.00000000E-001  -4.00000000E-001  1.00000000E-001  -4.00000000E-001  -7.00000000E-001  -9.00000000E-001  -8.00000000E-001  -1.30000000E+000  -1.30000000E+000  -1.30000000E+000  -1.40000000E+000  -2.10000000E+000  -1.20000000E+000  -1.20000000E+000  -1.70000000E+000  -1.60000000E+000  -1.60000000E+000  -1.60000000E+000  -1.00000000E+000  -1.00000000E+000  -8.00000000E-001  -1.30000000E+000  -1.10000000E+000  -1.40000000E+000  5.00000000E-001,
</pre>
<br/>

### HISTORY_HEADER Block (mandatory)

| Block Name     | Field Name    | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value |       Null Value        |
|----------------|---------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:-----------------------:|
| HISTORY_HEADER | CREATION_DATE |         n         |  SYTM  |         y         |           1           |     empty     | 17-NOV-1858 00:00:00.00 |
| HISTORY_HEADER | PROCESS       |         n         | string |         n         |          0…n          |     empty     |          none           |

Table 10 - HISTORY_HEADER block details

<br/>

The HISTORY_HEADER block is mandatory.

All fields in the HISTORY_HEADER block are mandatory.

The fields are order dependent and must conform to the above order.

All HISTORY_HEADER blocks must be grouped together.

The HISTORY_HEADER block(s) precede the PARAMETER_HEADER block(s).

An example HISTORY_HEADER block follows:

<pre>
HISTORY_HEADER
  CREATION_DATE = '04-JUN-1999 14:47:40.37'
  PROCESS = 'SELECT_FILE,FILE_SPEC=D7:CTD_96006*.ODF'
</pre>
<br/>
<hr/>

### PARAMETER_HEADER Block (mandatory)

| Block Name       | Field Name           | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value | Null Value |
|------------------|----------------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:----------:|
| PARAMETER_HEADER | TYPE                 |         n         | string |         n         |           1           |     empty     |    none    |
| PARAMETER_HEADER | NAME                 |         n         | string |         n         |           1           |     empty     |    none    |
| PARAMETER_HEADER | UNITS                |         n         | string |         y         |           1           |     empty     |    none    |
| PARAMETER_HEADER | CODE                 |         y         | string |         y         |           1           |     empty     |    none    |
| PARAMETER_HEADER | NULL_VALUE           |         n         | string |         y         |           1           |     empty     |    none    |
| PARAMETER_HEADER | PRINT_FIELD_ORDER    |         n         | number |         y         |           1           |     empty     |    none    |
| PARAMETER_HEADER | PRINT_FIELD_WIDTH    |         n         | number |         n         |           1           |     empty     |    none    |
| PARAMETER_HEADER | PRINT_DECIMAL_PLACES |         n         | number |         n         |           1           |     empty     |    none    |
| PARAMETER_HEADER | ANGLE_OF_SECTION     |         n         | number |         n         |           1           |     empty     |    -99     |
| PARAMETER_HEADER | MAGNETIC_VARIATION   |         n         | number |         n         |           1           |     empty     |    -99     |
| PARAMETER_HEADER | DEPTH                |         n         | number |         n         |           1           |     empty     |    -99     |
| PARAMETER_HEADER | MINIMUM_VALUE        |         n         | number |         n         |           1           |     empty     |    -99     |
| PARAMETER_HEADER | MAXIMUM_VALUE        |         n         | number |         n         |           1           |     empty     |    -99     |
| PARAMETER_HEADER | NUMBER_VALID         |         n         | number |         y         |           1           |     empty     |    -99     |
| PARAMETER_HEADER | NUMBER_NULL          |         n         | number |         y         |           1           |     empty     |    -99     |

Table 11 - PARAMETER_HEADER block details

<br/>

At least one PARAMETER_HEADER block is mandatory.

Multiple PARAMETER_HEADER blocks are permitted within the ODF file.

All fields in the PARAMETER_HEADER block are mandatory.

The mandatory fields are:

- TYPE
- CODE
- ANGLE_OF_SECTION
- MAGNETIC_VARIATION
- DEPTH
- PRINT_FIELD_ORDER

The fields in the PARAMETER_HEADER block are not order dependent.

The order of the individual PARAMETER_HEADER blocks is independent of
the order of the data channels within the data section of the ODF file.

All PARAMETER_HEADER blocks must be grouped together.

The PARAMETER_HEADER block(s) follow the HISTORY_HEADER block(s).

All data parameters in an ODF file must have a valid parameter code.

An example PARAMETER_HEADER block follows:

<pre>
PARAMETER_HEADER,
  TYPE = 'DOUB',
  NAME = 'Sea Pressure (sea surface - 0)',
  UNITS = 'decibars',
  CODE = 'PRES_01',
  NULL_VALUE = 173.00,
  PRINT_FIELD_WIDTH = 10,
  PRINT_DECIMAL_PLACES = 3,
  ANGLE_OF_SECTION = 0.000000,
  MAGNETIC_VARIATION = 0.000000,
  DEPTH = 0.000000,
  MINIMUM_VALUE = 1.2,
  MAXIMUM_VALUE = 35.6,
  NUMBER_VALID = -99,
  NUMBER_NULL = 0,
</pre><br/>

The following table lists all of the valid parameter codes:

<details class="code-fold">
<summary>Code</summary>

``` python
import pandas as pd
from tabulate import tabulate
import IPython.display as d

df = pd.read_csv("gf3defs_sorted.csv")
md = tabulate(df, headers='keys', tablefmt='pipe',showindex=False)
d.Markdown(md)
```

</details>

| Code     | Description                                                                    | Units                       | Field Width | Decimal Places |
|:---------|:-------------------------------------------------------------------------------|:----------------------------|------------:|---------------:|
| 412E     | Irradiance 412nm                                                               | uW/cm\*\*2/nm               |          10 |              5 |
| 412E     | Irradiance 412nm                                                               | uW/cm\*\*2/nm               |          13 |              5 |
| 412ESDEV | Irradiance 412nm standard deviation                                            | uW/cm\*\*2/nm               |          10 |              5 |
| 412ESDEV | Irradiance 412nm standard deviation                                            | uW/cm\*\*2/nm               |          13 |              5 |
| 412L     | Radiance 412nm                                                                 | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 412L     | Radiance 412nm                                                                 | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 412LSDEV | Radiance 412nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 412LSDEV | Radiance 412nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 443E     | Irradiance 443nm                                                               | uW/cm\*\*2/nm               |          10 |              5 |
| 443E     | Irradiance 443nm                                                               | uW/cm\*\*2/nm               |          13 |              5 |
| 443ESDEV | Irradiance 443nm standard deviation                                            | uW/cm\*\*2/nm               |          10 |              5 |
| 443ESDEV | Irradiance 443nm standard deviation                                            | uW/cm\*\*2/nm               |          13 |              5 |
| 443L     | Radiance 443nm                                                                 | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 443L     | Radiance 443nm                                                                 | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 443LSDEV | Radiance 443nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 443LSDEV | Radiance 443nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 490E     | Irradiance 490nm                                                               | uW/cm\*\*2/nm               |          10 |              5 |
| 490E     | Irradiance 490nm                                                               | uW/cm\*\*2/nm               |          13 |              5 |
| 490ESDEV | Irradiance 490nm standard deviation                                            | uW/cm\*\*2/nm               |          10 |              5 |
| 490ESDEV | Irradiance 490nm standard deviation                                            | uW/cm\*\*2/nm               |          13 |              5 |
| 490L     | Radiance 490nm                                                                 | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 490L     | Radiance 490nm                                                                 | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 490LSDEV | Radiance 490nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 490LSDEV | Radiance 490nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 510E     | Irradiance 510nm                                                               | uW/cm\*\*2/nm               |          10 |              5 |
| 510E     | Irradiance 510nm                                                               | uW/cm\*\*2/nm               |          13 |              5 |
| 510ESDEV | Irradiance 510nm standard deviation                                            | uW/cm\*\*2/nm               |          10 |              5 |
| 510ESDEV | Irradiance 510nm standard deviation                                            | uW/cm\*\*2/nm               |          13 |              5 |
| 510L     | Radiance 510nm                                                                 | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 510L     | Radiance 510nm                                                                 | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 510LSDEV | Radiance 510nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 510LSDEV | Radiance 510nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 555E     | Irradiance 555nm                                                               | uW/cm\*\*2/nm               |          10 |              5 |
| 555E     | Irradiance 555nm                                                               | uW/cm\*\*2/nm               |          13 |              5 |
| 555ESDEV | Irradiance 555nm standard deviation                                            | uW/cm\*\*2/nm               |          10 |              5 |
| 555ESDEV | Irradiance 555nm standard deviation                                            | uW/cm\*\*2/nm               |          13 |              5 |
| 555L     | Radiance 555nm                                                                 | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 555L     | Radiance 555nm                                                                 | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 555LSDEV | Radiance 555nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 555LSDEV | Radiance 555nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 669E     | Irradiance 669nm                                                               | uW/cm\*\*2/nm               |          10 |              5 |
| 669E     | Irradiance 669nm                                                               | uW/cm\*\*2/nm               |          13 |              5 |
| 669ESDEV | Irradiance 669nm standard deviation                                            | uW/cm\*\*2/nm               |          10 |              5 |
| 669ESDEV | Irradiance 669nm standard deviation                                            | uW/cm\*\*2/nm               |          13 |              5 |
| 669L     | Radiance 669nm                                                                 | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 669L     | Radiance 669nm                                                                 | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 669LSDEV | Radiance 669nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 669LSDEV | Radiance 669nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 683E     | Irradiance 683nm                                                               | uW/cm\*\*2/nm               |          10 |              5 |
| 683E     | Irradiance 683nm                                                               | uW/cm\*\*2/nm               |          13 |              5 |
| 683ESDEV | Irradiance 683nm standard deviation                                            | uW/cm\*\*2/nm               |          10 |              5 |
| 683ESDEV | Irradiance 683nm standard deviation                                            | uW/cm\*\*2/nm               |          13 |              5 |
| 683L     | Radiance 683nm                                                                 | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 683L     | Radiance 683nm                                                                 | uW/cm\*\*2/nm/sr            |          13 |              5 |
| 683LSDEV | Radiance 683nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          10 |              5 |
| 683LSDEV | Radiance 683nm standard deviation                                              | uW/cm\*\*2/nm/sr            |          13 |              5 |
| ABSH     | Absolute Humidity                                                              | g/m\*\*3                    |          10 |              3 |
| ALKY     | Total Alkalinity                                                               | mmol/m\*\*3                 |          10 |              3 |
| ALPO     | Alpha - 0                                                                      | m\*\*3/kg                   |          10 |              3 |
| ALTB     | Height/Altitude above Bottom                                                   | metres                      |          10 |              2 |
| ALTS     | Height/Altitude above Mean Sea Level                                           | metres                      |          10 |              3 |
| AMON     | Ammonium (NH4-N) Content                                                       | mmol/m\*\*3                 |          10 |              3 |
| ATMP     | Atmospheric pressure                                                           | hPa                         |          10 |              2 |
| ATMS     | Atmospheric Pressure at Sea Level                                              | hpa                         |          10 |              3 |
| ATP\_    | Adenosine Triphosphate content                                                 | mg/m\*\*3                   |          10 |              5 |
| ATRK     | Along Track Displacement                                                       | metres                      |          10 |              3 |
| ATTU     | Attenuance (ADCP)                                                              | /m                          |          10 |              3 |
| AUTH     | Authority                                                                      | none                        |          50 |            -99 |
| BAC\_    | Bacteria Counts                                                                | 10\*\*6/L                   |          10 |              3 |
| BATH     | Bathymetric Depth                                                              | metres                      |          10 |              3 |
| BATT     | Battery Voltage                                                                | volts                       |          10 |              3 |
| BEAM     | ADCP Echo Intensity                                                            | none                        |           6 |              1 |
| BIOV     | Organism Volume                                                                | mL                          |           8 |              3 |
| BNO7     | Best NODC7 number                                                              | none                        |          12 |              0 |
| CALK     | Carbonate Alkalinity                                                           | mmol/m\*\*3                 |          10 |              3 |
| CAL\_    | Detail data: Calorimetric bomb                                                 | cal/mg                      |          10 |              5 |
| CDOM     | Fluorescence of CDOM (Coloured Dissolved Organic Matter)                       | mg/m\*\*3                   |          10 |              3 |
| CDOMSDEV | Fluorescence of CDOM (Coloured Dissolved Organic Matter) standard deviation    | mg/m\*\*3                   |          10 |              3 |
| CDOMSDEV | Fluorescence of CDOM (Coloured Dissolved Organic Matter) standard deviation    | mg/m\*\*3                   |          10 |              3 |
| CDWT     | Detail data: Calculated dry weight derived using a regression                  | mg/m³                       |          10 |              5 |
| CHLR     | Chlorinity (parts/thousand)                                                    | g/kg                        |          10 |              3 |
| CHLS     | Chlorosity                                                                     | kg/m\*\*3                   |          10 |              3 |
| CMET     | Method used for sample collection                                              | none                        |          50 |            -99 |
| CMNT     | Comments                                                                       | none                        |        1000 |            -99 |
| CMTM     | CMCTD Time YYJJJHHMMSSss                                                       | GMT                         |          10 |              3 |
| CNDC     | Electrical Conductivity                                                        | mhos/m                      |          10 |              5 |
| CNTR     | Counter                                                                        | none                        |          10 |              3 |
| CNTS     | Number of Organisms Counted                                                    | none                        |           4 |              0 |
| COLL     | Detail data: Name of the collector for the data                                | none                        |          30 |            -99 |
| COND     | Conductivity                                                                   | mmHo                        |          10 |              5 |
| CORG     | Organic Carbon Content                                                         | mmol/m\*\*3                 |          10 |              3 |
| CPCT     | Identifies the Percentage of Specified Plankton                                | %                           |           6 |              3 |
| CPHL     | Chlorophyll-a Content                                                          | mg/m\*\*3                   |          10 |              3 |
| CRAT     | Conductivity Ratio                                                             | none                        |          10 |              5 |
| CTAX     | Collector Taxonomic Identifier                                                 | none                        |          20 |            -99 |
| CTOT     | Total Carbon (C) Content                                                       | mmol/m\*\*3                 |          10 |              3 |
| DCHG     | Discharge                                                                      | m\*\*3/s                    |           9 |              2 |
| DENS     | Sea Density                                                                    | kg/m\*\*3                   |          10 |              4 |
| DEPH     | Sensor Depth below Sea Surface                                                 | metres                      |          10 |              2 |
| DEWT     | Dew Point Temperature                                                          | degrees C                   |          10 |              3 |
| DOC\_    | Dissolved Organic Carbon content                                               | mmol/m\*\*3                 |          10 |              3 |
| DON\_    | Dissolved Organic Nitrogen content                                             | mmol/m\*\*3                 |          10 |              3 |
| DOXY     | Dissolved Oxygen                                                               | ml/l                        |          10 |              3 |
| DPDT     | Lowering Rate                                                                  | metres/sec                  |          10 |              3 |
| DRDP     | Depth of Drogue                                                                | metres                      |          10 |              3 |
| DRWT     | Dry Weight of Organisms                                                        | g                           |          10 |              5 |
| DRYT     | Dry Bulb Temperature                                                           | degrees C                   |          10 |              3 |
| DYNH     | Geopotential Dynamic Height                                                    | m                           |          10 |              3 |
| ERRV     | Error Velocity (ADCP)                                                          | m/s                         |          10 |              4 |
| EWCM     | East (magnetic) Component of Current                                           | m/s                         |          10 |              3 |
| EWCT     | East (true) Component of Current                                               | m/s                         |          10 |              4 |
| FFFF     | Quality Control Flag                                                           | code                        |          10 |              3 |
| FLOR     | Fluorescence                                                                   | mg/m\*\*3                   |          10 |              3 |
| FLORSDEV | Fluorescence standard deviation                                                | mg/m\*\*3                   |          10 |              3 |
| FLORSDEV | Fluorescence standard deviation                                                | mg/m\*\*3                   |          10 |              3 |
| FLU\_    | Fluorescence                                                                   | %                           |          10 |              3 |
| GDIR     | Gust Wind Direction                                                            | degrees                     |          10 |              3 |
| GEAR     | Gear used for sample collection                                                | none                        |          50 |            -99 |
| GEOP     | Geopotential                                                                   | none                        |          10 |              3 |
| GSPD     | Gust Wind Speed                                                                | m/s                         |          10 |              3 |
| HCDM     | Horizontal Current Direction (magnetic)                                        | degrees                     |          10 |              3 |
| HCDT     | Horizontal Current Direction (true)                                            | degrees                     |          10 |              3 |
| HCSP     | Horizontal Current Speed                                                       | m/s                         |          10 |              3 |
| HEAD     | Heading                                                                        | True degrees                |           6 |              1 |
| HEAD     | Heading                                                                        | True degrees                |           6 |              1 |
| HGHT     | Height/Altitude above Sea Surface                                              | metres                      |          10 |              3 |
| HSUL     | Hydrogen Sulphide (H2S-S) Content                                              | mmol/m\*\*3                 |          10 |              3 |
| IDEN     | Data identifier                                                                | none                        |          10 |              0 |
| LATD     | Latitude (North +ve)                                                           | degrees                     |          10 |              4 |
| LCHL     | Chlorophyll-a Content from cells \> 5um                                        | mg/m\*\*3                   |          10 |              3 |
| LHIS     | Life History or Development Stage                                              | none                        |          50 |            -99 |
| LOND     | Longitude (East +ve)                                                           | degrees                     |          10 |              4 |
| LPHA     | Phaeopigment content from cells \> 5um                                         | mg/m\*\*3                   |          10 |              3 |
| MAGN     | Magnetic Variation From True North                                             | degrees                     |          10 |              3 |
| MNSV     | Retention Filter Size                                                          | microns                     |           6 |              0 |
| MNSZ     | Minimum size of organisms                                                      | microns                     |           6 |              0 |
| MODF     | Additional taxonomic information                                               | none                        |          50 |            -99 |
| MXSV     | Largest Sieve Used                                                             | microns                     |           6 |              0 |
| MXSZ     | Maximum size of organisms                                                      | microns                     |           6 |              0 |
| NETR     | Net Solar Radiation                                                            | watts/m\*\*2                |          10 |              3 |
| NONE     | No WMO assigned                                                                | none                        |          10 |              3 |
| NORG     | Organic Nitrogen Content                                                       | mmol/m\*\*3                 |          10 |              3 |
| NSCM     | North (magnetic) Component of Current                                          | m/s                         |          10 |              3 |
| NSCT     | North (true) Component of Current                                              | m/s                         |          10 |              4 |
| NTOT     | Total Nitrogen (N) Content                                                     | mmol/\*\*3                  |          10 |              3 |
| NTRA     | Nitrate (NO3-N) Content                                                        | mmol/m\*\*3                 |          10 |              3 |
| NTRI     | Nitrite (NO2-N) Content                                                        | mmol/m\*\*3                 |          10 |              3 |
| NTRZ     | Nitrate + Nitrite Content                                                      | mmol/m\*\*3                 |          10 |              3 |
| NUM\_    | Number of scans averaged                                                       | none                        |          10 |              0 |
| OCUR     | Oxygen Sensor Current                                                          | uA                          |          10 |              3 |
| OPPR     | Oxygen Partial Pressure                                                        | none                        |          10 |              3 |
| OSAT     | Oxygen Saturation                                                              | %                           |          10 |              3 |
| OTMP     | Oxygen Sensor Temperature                                                      | degrees C                   |          10 |              3 |
| OXV\_    | Raw oxygen voltage                                                             | volts                       |          10 |              3 |
| OXYG     | Dissolved Oxygen                                                               | umol/kg                     |          10 |              3 |
| PCGD     | Percent Good Signal Return (ADCP)                                              | %                           |           5 |              0 |
| PGDP     | Percent Good Pings                                                             | %                           |          10 |              3 |
| PHA\_    | Phaeopigment content                                                           | mg/m\*\*3                   |          10 |              3 |
| PHOS     | Phosphate (PO4-P) Content                                                      | mmol/m\*\*3                 |          10 |              3 |
| PHPH     | Hydrogen Ion Concentration (pH)                                                | none                        |          10 |              3 |
| PHY\_    | Phytoplankton Counts                                                           | 10\*\*3cells/L              |          10 |              3 |
| PIM\_    | Bottle sample particulate inorganic matter                                     | g/m\*\*3                    |          10 |              3 |
| PLT\_    | Percentage of the incident surface light remaining at the sampled depth        | %                           |          10 |              3 |
| POC\_    | Particulate Organic Carbon content                                             | mmol/m\*\*3                 |          10 |              3 |
| POM\_    | Bottle sample particulate organic matter                                       | g/m\*\*3                    |          10 |              3 |
| PON\_    | Particulate Organic Nitrogen content                                           | mmol/m\*\*3                 |          10 |              3 |
| POTM     | Potential Temperature                                                          | degrees C                   |          10 |              4 |
| POTT     | Potential Air Temperature                                                      | degrees C                   |          10 |              4 |
| PPR\_    | Primary Production                                                             | mgC/m\*\*3/h                |          10 |              2 |
| PPTR     | PIPE Internal Pointer                                                          | none                        |          10 |              3 |
| PRES     | Sea Pressure (sea surface - 0)                                                 | decibars                    |          10 |              2 |
| PROC     | Identifies the state of the sample analysis                                    | none                        |          50 |            -99 |
| PRP\_    | Production primaire à partir d\`incubations                                    | mgC/m\*\*3/h                |          10 |              3 |
| PRSN     | Indicates presence (1) or absence (0) of organisms if not counted              | none                        |           3 |              0 |
| PRSV     | Method used for sample preservation                                            | none                        |          50 |            -99 |
| PSAL     | Practical Salinity                                                             | psu                         |          10 |              4 |
| PSAR     | Photosynthetic Active Radiation                                                | ueinsteins/s/m\*\*2         |          10 |              3 |
| PTCH     | Pitch Angle                                                                    | degrees                     |           6 |              1 |
| PTCHSDEV | Pitch Angle standard deviation                                                 | degrees                     |          10 |              3 |
| PTCHSDEV | Pitch Angle standard deviation                                                 | degrees                     |           6 |              1 |
| PVAR     | PIPE Variable                                                                  | none                        |          10 |              3 |
| QCFF     | Quality flag: QCFF                                                             | none                        |           5 |              0 |
| QQQQ     | Quality Control Flag (GTSPP)                                                   | none                        |          10 |              3 |
| RANG     | Distance of Object from Reference Point                                        | metres                      |          10 |              3 |
| REFR     | Reference                                                                      | none                        |          10 |              3 |
| RELH     | Relative Humidity                                                              | %                           |          10 |              3 |
| RELP     | Relative Total Pressure                                                        | decibars                    |          10 |              3 |
| ROLL     | Roll Angle                                                                     | degrees                     |           6 |              1 |
| ROLLSDEV | Roll Angle standard deviation                                                  | degrees                     |          10 |              3 |
| ROLLSDEV | Roll Angle standard deviation                                                  | degrees                     |           6 |              1 |
| RPOT     | Redox Potential                                                                | mV                          |          10 |              3 |
| SDEV     | Standard deviation of preceding parameter                                      | same as preceding parameter |          10 |              3 |
| SECC     | SECCHI disc depth                                                              | m                           |          10 |              1 |
| SEX\_    | Sex                                                                            | none                        |          50 |            -99 |
| SIGO     | Sigma-0                                                                        | kg/m\*\*3                   |          10 |              4 |
| SIGP     | Sigma-Theta                                                                    | kg/m\*\*3                   |          10 |              4 |
| SIGT     | Sigma-T                                                                        | kg/m\*\*3                   |          10 |              4 |
| SLCA     | Silicate (SIO4-SI) Content                                                     | mmol/m\*\*3                 |          10 |              3 |
| SNCN     | Scan Counter                                                                   | none                        |          10 |              3 |
| SPAR     | Surface Photosynthetic Active Radiation                                        | ueinsteins/s/m\*\*2         |          10 |              3 |
| SPARSDEV | Surface Photosynthetic Active Radiation standard deviation                     | ueinsteins/s/m\*\*2         |          10 |              3 |
| SPARSDEV | Surface Photosynthetic Active Radiation standard deviation                     | ueinsteins/s/m\*\*2         |          10 |              3 |
| SPEH     | Specific Humidity                                                              | g/kg                        |          10 |              3 |
| SPFR     | Fraction of Sample                                                             | none                        |           6 |              4 |
| SPVA     | Specific Volume Anomoly                                                        | m\*\*3/kg                   |          10 |              3 |
| SPVO     | Specific Volume                                                                | m\*\*3/kg                   |          10 |              3 |
| SSAL     | Salinity                                                                       | g/kg or o/oo                |          10 |              3 |
| STOR     | Description of sample storage between collection and analysis                  | none                        |          50 |            -99 |
| STRA     | Stress Amplitude                                                               | Pa                          |          10 |              3 |
| STRD     | Stress Direction                                                               | degrees T                   |          10 |              3 |
| STRU     | Stress (U Component)                                                           | Pa                          |          10 |              3 |
| STRV     | Stress (V Component)                                                           | Pa                          |          10 |              3 |
| SVEL     | Sound Velocity                                                                 | m/s                         |          10 |              3 |
| SYTM     | PIPE Time Format DD-MMM-YYYY HH:MM:SS.ss                                       | GMT                         |          23 |              0 |
| TAXN     | Taxonomic Name                                                                 | none                        |          50 |            -99 |
| TE90     | Temperature (ITS-90 scale)                                                     | degrees C                   |          10 |              4 |
| TEMP     | Temperature (IPTS-68 Scale)                                                    | degrees C                   |          10 |              4 |
| TEXT     | Plain Language Text                                                            | none                        |          10 |              3 |
| TILT     | Tilt Angle                                                                     | degrees                     |           6 |              1 |
| TILTSDEV | Tilt Angle standard deviation                                                  | degrees                     |          10 |              3 |
| TILTSDEV | Tilt Angle standard deviation                                                  | degrees                     |           6 |              1 |
| TLENBSEQ | Frequency data: Sequential number attached to bugs having a given total length | nan                         |           4 |              0 |
| TLENCNTP | Frequency data: Percentage of bugs having a given total length                 | %                           |           6 |              1 |
| TLENCOLL | Frequency data: Name of the collector                                          | nan                         |          30 |            -99 |
| TLENLBIN | Frequency data: Bug total length lower frequency bin                           | mm                          |           7 |              3 |
| TLENQQQQ | Frequency data: Quality control code of bugs having a given total length       | nan                         |           1 |              0 |
| TLENTLEN | Frequency data: Bug total length                                               | mm                          |           7 |              3 |
| TLENUBIN | Frequency data: Bug total length upper frequency bin                           | mm                          |           7 |              3 |
| TOFF     | CMCTD Time Offset                                                              | s                           |          10 |              3 |
| TOTP     | Total Pressure (Atmosphere + Sea Pressure)                                     | decibars                    |          10 |              3 |
| TPHS     | Total Phosphorous (P) Content                                                  | mmol/m\*\*3                 |          10 |              3 |
| TRAN     | Light Transmission                                                             | %                           |          10 |              3 |
| TRPH     | Trophic Descriptor                                                             | none                        |          50 |            -99 |
| TSM\_    | Bottle sample total suspended matter                                           | g/m\*\*3                    |          10 |              3 |
| TSN\_    | Taxonomic Serial Number                                                        | none                        |          12 |              0 |
| TURB     | OBS Turbidity                                                                  | FTU                         |          10 |              4 |
| UNKN     | Unknown WMO Code                                                               | none                        |          10 |              3 |
| URE\_    | Urea content                                                                   | mmol/m\*\*3                 |          10 |              3 |
| VAIS     | Brunt Vaissala Frequency                                                       | hertz                       |          10 |              3 |
| VCSP     | Vertical Current Speed (positive up)                                           | m/s                         |          10 |              4 |
| VMET     | Method used to determine the volume of water                                   | none                        |          50 |            -99 |
| VOLT     | Sensor Volts                                                                   | volts                       |          10 |              4 |
| WDIR     | Wind Direction relative to North (T)                                           | degrees                     |          10 |              3 |
| WETECOBB | Turbidity, WET Labs ECO BB                                                     | m^-1/sr                     |          10 |              4 |
| WETT     | Wet Bulb Temperature                                                           | degrees C                   |          10 |              3 |
| WSPD     | Horizontal Wind Speed                                                          | m/s                         |          10 |              3 |
| WSPE     | Eastward (true) Component of Wind Speed                                        | m/s                         |          10 |              3 |
| WSPN     | Northward (True) Component of Wind Speed                                       | m/s                         |          10 |              3 |
| WTWT     | Wet Weight of Organisms                                                        | g                           |          10 |              5 |
| WVER     | Vertical Wind Speed                                                            | m/s                         |          10 |              3 |
| ZNTH     | Zenith Angle of Object From Reference                                          | degrees                     |          10 |              3 |
| ZOO\_    | Zooplankton counts                                                             | none                        |          15 |              3 |

Table 12 - Parameter codes

### RECORD_HEADER Block (mandatory)

| Block Name    | Field Name      | Restricted Values |  Type  | Content Mandatory | Number of Occurrences | Default Value | Null Value |
|---------------|-----------------|:-----------------:|:------:|:-----------------:|:---------------------:|:-------------:|:----------:|
| RECORD_HEADER | NUM_CALIBRATION |         n         | number |         y         |           1           |     empty     |    none    |
| RECORD_HEADER | NUM_SWING       |         n         | number |         y         |           1           |     empty     |    none    |
| RECORD_HEADER | NUM_HISTORY     |         n         | number |         y         |           1           |     empty     |    none    |
| RECORD_HEADER | NUM_CYCLE       |         n         | number |         y         |           1           |     empty     |    none    |
| RECORD_HEADER | NUM_PARAM       |         n         | number |         y         |           1           |     empty     |    none    |

Table 13 - RECORD_HEADER block details

<br/>

One RECORD_HEADER block must exist in an ODF file.

All fields are mandatory.

The fields do not have a required order.

The RECORD_HEADER block identifies the number of calibration (polynomial
or general) blocks, swing (compass) blocks, history blocks, data cycles
(records or rows) and parameters in the ODF file.

The RECORD_HEADER block follow the PARAMETER_HEADER block(s).

<pre>
RECORD_HEADER,
  NUM_CALIBRATION = 0
  NUM_SWING = 0
  NUM_HISTORY = 5
  NUM_CYCLE = 372
  NUM_PARAM = 8
</pre>

## ODF Data Section

The ODF data section is the part of the file following the – DATA –
identifier.

– DATA – (which is dash dash space DATA space dash dash)

The line that follows this one is the column header line. This line
contains a comma delimited list of all parameter codes associated with
the values in the data records.

Each code matches what is given in their corresponding PARAMETER_HEADER.

### Date-Time Fields in the Data Block

Date-Time values in the data section of the ODF file must be in SYTM
format.

In the data section, the character space occupied by the leading and
trailing single quotes are not counted in the value noted within the
PARAMETER_HEADER block field named PRINT_FIELD_WIDTH.

### Data Values

The data values in the data section of the ODF file will conform to the
print and decimal specifications defined for each parameter in the
PARAMETER_HEADER fields denoted PRINT_FIELD_WIDTH and
PRINT_DECIMAL_PLACES.

Each data record will be comma delimited.

## Version 3.0 Release Notes

The list of changes from version 2.0 to 3.0 of the ODF file format
specification follows:

- Added the field ODF_SPECIFICATION_VERSION to the ODF_HEADER to
  identify which version of the ODF specification the file follows.
  Default value is 3.0.
- Commas at the end of header lines are no longer required, expected or
  recommended.
- Added the field AREA_OF_OPERATION to the CRUISE_HEADER instead of
  using the practice of using CRUISE_NAME to hold that information.
- Added the field PRINT_FIELD_ORDER to the PARAMETER_HEADER to identify
  its corresponding column in the data section.
- All fields in the PARAMETER_HEADER and RECORD_HEADER are now
  mandatory.
- The order of the PARAMETER_HEADER blocks can now be independent of the
  order of the data columns in the data section.
- The data section in an ODF file now starts with a column header line
  that is a list of parameter codes delimited by commas.
- The data records are no longer delimited by whitespace; instead they
  are now comma delimited records.
- Added the GENERAL_CAL_HEADER, QUALITY_HEADER, and METEO_HEADER blocks.
