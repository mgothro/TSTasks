from datetime import datetime
import csv
import re

def get_headers_sql(result_set):
    # returns an ordered list of column headers from a sql results object
    r = [x[0] for x in result_set[0].cursor_description]
    return r

def extract_data_rows_sql(result_set):
    # returns a list of rows that represent the rows of a sql results object
    r = []
    for row in result_set[0:]:
        r.append(row)

    return r

def convert_mdtm_to_datetime(mdtm):
    # Convert a string in the format 'YYYYMMDDHHMMSS' to a datetime object
    # Ex: 213 20231025040006
    year = int(mdtm[4:8])
    month = int(mdtm[8:10])
    day = int(mdtm[10:12])
    hour = int(mdtm[12:14])
    minute = int(mdtm[14:16])
    second = int(mdtm[16:18])

    # Create a datetime object
    return datetime(year, month, day, hour, minute, second)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def write_csv_from_data(result_set, file_path, include_headers=True, custom_headers=None):
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            csv_writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')

            # Write headers only if include_headers is True and custom_headers is not provided
            if include_headers:
                if custom_headers:
                    for header_row in custom_headers:
                        csv_writer.writerow(header_row)
                else:
                    csv_writer.writerow(get_headers_sql(result_set))

            for row in result_set:
                csv_row = []
                for field in row:
                    csv_row.append(field)

                csv_writer.writerow(csv_row)
            print(f"Results successfully written to {file_path}")
    except Exception as e:
        print(f"Failed to post results to csv: {e}")

def is_valid_email(email):
    # Define the regular expression for a valid email address
    email_regex = re.compile(
        r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    )
    # Check if the email matches the regular expression
    return re.match(email_regex, email) is not None


def convert_rows_to_json_serializable(rows):
    """
    Convert pyodbc.Row objects to a JSON-serializable list of dictionaries.

    :param rows: List of pyodbc.Row objects
    :param column_names: List of column names
    :return: List of dictionaries, each representing a row
    """
    # Combine column names with row values into dictionaries
    return [dict(zip(get_headers_sql(rows), row)) for row in rows]

class CaseInsensitiveDict(dict):
    """Case-insensitive dictionary implementation."""

    def __init__(self, data=None, **kwargs):
        super().__init__()
        self._convert_keys(data)
        self._convert_keys(kwargs)

    def _convert_keys(self, data):
        if data is None:
            return

        if isinstance(data, zip):  # Check if data is a zip object
            # Convert the zip object to a dictionary before processing
            data = dict(data)

        if isinstance(data, dict): #Only continue if this is a dict.
            for key, value in data.items():
                self[key] = value
        else:
            raise TypeError("Data must be a dictionary or a zip object that can be converted to a dictionary.")

    def __setitem__(self, key, value):
        if isinstance(key, str):  # Check if the key is a string
            super().__setitem__(key.lower(), value)
        else:
            super().__setitem__(key, value)  # Store the key as is

    def __getitem__(self, key):
        if isinstance(key, str):  # Check if the key is a string
            return super().__getitem__(key.lower())
        else:
            return super().__getitem__(key)

    def __contains__(self, key):
        if isinstance(key, str):  # Check if the key is a string
            return super().__contains__(key.lower())
        else:
            return super().__contains__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        try:
            value = self[key]
            del self[key]
            return value
        except KeyError:
            if default is not None:
                return default
            raise

    def setdefault(self, key, default=None):
        key_lower = key.lower()
        if key_lower not in self:
            self[key] = default
        return self[key]

    def copy(self):
        return CaseInsensitiveDict(super().copy())
