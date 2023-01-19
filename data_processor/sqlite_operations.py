
# standard
import logging
import time
# external
import sqlite3
# local
from data_classes import Listing


def get_sqlite_data_type(python_object: object) -> str:
    """
    Get SQLite data type of input object.

    :param python_object: Any Python object.
    :return: SQLite data type of input object.
    """
    object_type = type(python_object).__name__
    if object_type == "int":
        return "INTEGER"
    elif object_type == "float":
        return "REAL"
    elif object_type == "str":
        return "TEXT"
    elif object_type == "NoneType":
        return "NULL"
    else:
        return "BLOB"


def table_exists(name: str, connection: sqlite3.Connection) -> bool:
    """
    Check if table exists in SQLite.

    :param name: Table name to search.
    :param connection: SQL connection object.
    :return: True/False whether the table exists
    """
    check_table_query = f"SELECT EXISTS (SELECT name FROM sqlite_master WHERE type='table' AND name='{name}');"
    sql_cursor = connection.cursor()
    query_result = sql_cursor.execute(check_table_query)
    table_found = bool(query_result.fetchone()[0])
    return table_found


def create_listings_table(table: str, connection: sqlite3.Connection) -> None:
    """
    Creates table for listings to SQLite

    :param table: SQL listings table name
    :param connection: SQL connection object.
    :return: None
    """
    listing_columns_types = {key: get_sqlite_data_type(value) for key, value in vars(Listing()).items()}
    listing_columns_types_string = ",\n\t".join([f"{key} {value}" for key, value in listing_columns_types.items()])
    create_table_command = f"CREATE TABLE {table} (\n\t{listing_columns_types_string}\n);"
    sql_cursor = connection.cursor()
    sql_cursor.execute(create_table_command)
    return


def insert_listing(listing: Listing, table: str, connection: sqlite3.Connection) -> None:
    """
    Inserts a Listing to SQL table.

    :param listing: Listing type object to be inserted.
    :param table: Name of SQL table where the listing should be inserted to.
    :param connection: SQL connection object.
    :return: None
    """
    listing_columns = list()
    listing_values = list()
    for column, value in vars(listing).items():
        listing_columns += [column]
        listing_values += ["'" + str(value) + "'"]
    listing_columns_string = ",".join(listing_columns)
    listing_values_string = ",".join(listing_values)

    insert_listing_command = f"INSERT INTO {table} ({listing_columns_string})\n" + \
                             f"VALUES\n\t({listing_values_string});"

    sql_cursor = connection.cursor()
    try:
        sql_cursor.execute(insert_listing_command)
    except Exception as exception:
        log_string = f"{type(exception).__name__} error occurred, " + \
                     f"when trying to insert listing {listing} to SQL: {exception}"
        logging.exception(log_string)
        del log_string
    return


def get_where_statement(conditions: (dict, str, None)) -> str:
    """
    Turn input to a SQL WHERE statement
    :param conditions: dict with key: value pairs for columns and their values;
    str of a completed WHERE statement or None
    :return: A SQL WHERE statement in str format
    """
    if isinstance(conditions, str):
        return conditions
    if conditions is None:
        return ""
    condition_strings = list()
    for key, value in conditions.items():
        # Quote values that are strings
        condition_strings += [f'{key} = "{value}"'] if isinstance(value, str) else [f"{key} = {value}"]
    where_condition = " AND ".join(condition_strings)
    return where_condition


def read_data(table: str, connection: sqlite3.Connection, where: (None, str, dict) = None) -> list[dict]:
    """
    Get data from a SQL table.

    :param table: SQL table name.
    :param connection: SQL connection.
    :param where: Optional SQL WHERE filtering clause as dict
    or statement string: e.g. "column = value" or "column IN (1,2,3)".
    :return: A list of column_name:value dicts.
    """
    where_statement = f" WHERE {get_where_statement(where)}" if where else ""
    get_data_command = f"SELECT * FROM {table}{where_statement};"
    sql_cursor = connection.cursor()
    data = sql_cursor.execute(get_data_command).fetchall()
    data_column_names = [item[0] for item in sql_cursor.execute(get_data_command).description]

    data_rows = list()
    for row in data:
        data_row = {key: value for key, value in zip(data_column_names, row)}
        data_rows += [data_row]
    return data_rows


def deactivate_listing(table: str, connection: sqlite3.Connection, activate: bool = False, **kwargs) -> None:
    """
    Sets the 'active' column value for a row in SQL table.

    :param table: Listings table name.
    :param connection: SLQ connection object.
    :param activate: True if a listing needs to be activated instead of deactivated.
    :param kwargs: Key-value pairs to identify listing that needs to be changed
    :return: None
    """
    where_condition_elements = list()
    for key, value in kwargs.items():
        # Quote values that are strings
        where_condition_elements += [f'{key} = "{value}"'] if isinstance(value, str) else [f"{key} = {value}"]
    where_condition = " AND ".join(where_condition_elements)
    update_table_command = f"UPDATE {table} SET active = {int(activate)} WHERE {where_condition};"
    sql_cursor = connection.cursor()
    sql_cursor.execute(update_table_command)
    return


def set_unlisting_date(table: str, connection: sqlite3.Connection,
                       date: float = round(time.time(), 0), **kwargs) -> None:
    """
    Sets the 'date_unlisted' column value for a row in SQL table.

    :param table: Listings table name.
    :param connection: SLQ connection object.
    :param date: Unlisting time in epoch format.
    :param kwargs: Key-value pairs to identify listing that needs to be changed
    :return: None
    """
    where_condition_elements = list()
    for key, value in kwargs.items():
        # Quote values that are strings
        where_condition_elements += [f'{key} = "{value}"'] if isinstance(value, str) else [f"{key} = {value}"]
    where_condition = " AND ".join(where_condition_elements)
    update_table_command = f"UPDATE {table} SET date_unlisted = {date} WHERE {where_condition};"
    sql_cursor = connection.cursor()
    sql_cursor.execute(update_table_command)
    return


def set_value(table: str, connection: sqlite3.Connection, column: str, value: str, where: dict = None) -> None:
    """
    Sets the specified column value in SQL table.

    :param table: Table name in SQL database.
    :param connection: SLQ connection object.
    :param column: Column/parameter to change in table.
    :param value: Value to assign to the column.
    :param where: Key-value pairs to identify listing that needs to be changed or full SQL WHERE statement string.
    :return: None
    """
    where_statement = f" WHERE {get_where_statement(where)}" if where else ""
    update_table_command = f"UPDATE {table} SET {column} = {value}{where_statement};"
    sql_cursor = connection.cursor()
    sql_cursor.execute(update_table_command)
    return
