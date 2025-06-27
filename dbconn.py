import pyodbc as p
import settings as s
from misc import chunks, CaseInsensitiveDict

def get_connection(connection_name: str = s.DEFAULT_DB_SERVER) -> p.Connection:
    """
    Reads the specified section (e.g., 'DataConnSMS') from an INI file
    to get server, database, and trusted connection info, then returns
    a pyodbc Connection object.
    """
    DRIVER = "SQL Server"
    db_config = s.DATABASE_CONFIG.get(connection_name, None)

    if not db_config:
        error_msg = f"Section [{connection_name}] not found"
        raise ValueError(error_msg)

    server = db_config.get("server")
    database = db_config.get("database")

    try:
        connection_string = (f"Driver={{{DRIVER}}};"
                             f"Server={server};"
                             f"Database={database};"
                             "Trusted_Connection=yes;")
        conn = p.connect(connection_string)
        conn.autocommit = True
        return conn
    except p.Error as ex:
        raise

def execute_query(query: str, params=None, database_config: str = s.DEFAULT_DB_SERVER, include_description=False):
    """
    Executes a SQL query that may produce multiple result sets.
    Returns a list of result sets (each a list of pyodbc.Row objects).
    """
    if params is None:
        params = ()

    conn = None
    try:
        conn = get_connection(database_config)
        with conn.cursor() as cursor:
            try:
                cursor.execute(query, params)
            except p.Error as err:
                print("pyodbc raised error from SQL Server:")
                print(err)
                raise

            all_results = []
            while True:
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()

                    #useful if you want column names for otherwise empty result sets
                    if include_description:
                        all_results.append({
                            "columns": columns,
                            "rows": [dict(zip(columns, row)) for row in rows]
                        })
                    else:
                        all_results.append(rows_to_dicts(rows))

                if not cursor.nextset():
                    break

            return all_results[0] if len(all_results) == 1 else all_results

    except p.Error as ex:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def execute_many(sql: str,
                 data: list,
                 batch_size: int = 5000,
                 section_name: str = "SMS"):
    """
    Executes a batch insert/update using executemany with fast execution mode.

    Args:
        sql (str): The SQL query to execute.
        data (list): The list of tuples to insert/update.
        batch_size (int): The number of rows per batch. Defaults to 5000.
        section_name (str): The database connection section to use. Defaults to "SMS".

    Returns:
        int: The total number of rows inserted/updated.

    Raises:
        pyodbc.Error: If an error occurs during execution.
    """
    if not data:
        return 0

    conn = None
    total_rows = 0

    try:
        conn = get_connection(section_name)
        cursor = conn.cursor()
        cursor.fast_executemany = True

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]  # Get a chunk of the data
            cursor.executemany(sql, batch)
            conn.commit()
            total_rows += len(batch)

        return total_rows

    except p.Error as ex:
        if conn:
            conn.rollback()
        raise

    finally:
        if conn:
            conn.close()

def rows_to_dicts(rows):
    """
    Converts a list of pyodbc.Row objects to a list of dictionaries.

    Parameters:
        rows (list): A list of pyodbc.Row objects.  It is assumed all rows
                     have the same structure (column names and order).

    Returns:
        list: A list of dictionaries, where each dictionary represents a row
              and the keys are the column names. Returns an empty list if rows is empty.
              Returns None if it can't determine the cursor_description.
    """

    if not rows:
        return []  # Return an empty list if there are no rows

    # Attempt to get the cursor_description from the first row
    try:
        cursor_description = rows[0].cursor_description
    except AttributeError:
        print("Error: Could not determine cursor_description from rows.")
        return None  # Can't determine column names

    column_names = [column[0] for column in cursor_description]

    dicts = []
    for row in rows:
        dicts.append(CaseInsensitiveDict(zip(column_names, row)))  # Correct initialization
    return dicts