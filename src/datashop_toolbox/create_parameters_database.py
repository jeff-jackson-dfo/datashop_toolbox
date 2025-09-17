import csv
import sqlite3

# Use 'with' to connect to the SQLite database and automatically close the connection when done
with sqlite3.connect('C:/Dev/GitHub/odf_toolbox/database/parameters.db') as connection:

    # Create a cursor object
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS ODF_PARAMETERS")

    # Write the SQL command to create the Students table
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS ODF_PARAMETERS (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        description TEXT NOT NULL,
        units TEXT NOT NULL,
        print_field_width INTEGER NOT NULL,
        print_decimal_places INTEGER NOT NULL
    );
    '''

    # Execute the SQL command
    cursor.execute(create_table_query)

    # Commit the changes
    connection.commit()

    # Print a confirmation message
    print("Table 'ODF_PARAMETERS' created successfully!")
    
    # Insert data from CSV file into database table
    file_name = 'C:/Dev/GitHub/odf_toolbox/src/odf_toolbox/gf3defs_sorted.csv'

    # Open the CSV file for reading
    with open(file_name, 'r') as csv_file:
        
        csv_reader = csv.reader(csv_file)
        next(csv_reader)  # Skip the header row

        # Insert each row into the Customers table
        insert_records = "INSERT INTO ODF_PARAMETERS (code, description, units, print_field_width, print_decimal_places) VALUES (?, ?, ?, ?, ?)"

        # Importing the contents of the file  into our ODF_PARAMETERS table
        cursor.executemany(insert_records, csv_reader)
        connection.commit()

    print(f"Data imported successfully from {file_name}.")
