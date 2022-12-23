
import sqlite3
from data_processing import Listing
import logging
import time


def log_exceptions(*args, **kwargs):
    """
    Decorator function to log exceptions occurring in a function.
    Description of attempted actions can be supplied by a 'context' variable.
    """
    def inner_function(function):
        context = kwargs.get("context")
        if context:
            del kwargs["context"]
        try:
            return function(*args, **kwargs)
        except Exception as exception:
            log_string = f"In function {function.__name__}, " \
                         f"{type(exception).__name__} exception occurred: {exception}" \
                         f"{bool(context)*f', while {context}'}."
            logging.exception(log_string)
    return inner_function


def get_sqlite_data_type(python_object: object) -> str:
    """
    Get sqlite data type of input object.

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


@log_exceptions
def table_exists(name: str, connection: sqlite3.Connection) -> bool:
    """
    Check if table exists in SQLite.

    :param name: Table name to search.
    :param connection: SQL connection object.
    :return: True/False whether the table exists
    """
    check_table_query = f"SELECT EXISTS (SELECT name FROM sqlite_master WHERE type='table' " + \
                        f"AND name='{name}');"
    sql_cursor = connection.cursor()
    query_result = sql_cursor.execute(check_table_query)
    table_exists = bool(query_result.fetchone()[0])
    return table_exists


@log_exceptions
def create_listing_table(table: str, connection: sqlite3.Connection) -> None:
    """
    Creates table for listings to SQLite, using config.SQL_LISTING_TABLE_NAME as table name

    :param table: SQL listings table name
    :param connection: SQL connection object.
    :return: None
    """
    listing_columns_types = {key: get_sqlite_data_type(value) for key, value in vars(Listing()).items()}
    # Constrain id column to have non null unique values
    listing_columns_types["id"] = f"{listing_columns_types['id']} PRIMARY KEY NOT NULL"
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
    except sqlite3.Error as sql_error:
        log_string = f"In function {insert_listing.__name__}, {type(sql_error).__name__} error occurred " + \
                     f"with listing {listing}: {sql_error}"
        logging.error(log_string)
    return


@log_exceptions
def read_data(table: str, connection: sqlite3.Connection, where: (None, str) = None) -> list[dict]:
    """
    Get data from a SQL table.

    :param table: SQL table name.
    :param connection: SQL connection.
    :param where: Optional SQL WHERE filtering clause as string. E.g. "column = value" or "column IN (1,2,3)".
    :return: A list of column_name:value dicts.
    """
    if where is None:
        get_data_command = f"SELECT * FROM {table};"
    else:
        get_data_command = f"SELECT * FROM {table} WHERE {where};"
    sql_cursor = connection.cursor()
    data = sql_cursor.execute(get_data_command).fetchall()
    data_column_names = [item[0] for item in sql_cursor.execute(get_data_command).description]

    data_rows = list()
    for row in data:
        data_row = {key: value for key, value in zip(data_column_names, row)}
        data_rows += [data_row]

    return data_rows


@log_exceptions
def deactivate_id(listing_id: str, table: str, connection: sqlite3.Connection, activate: bool = False) -> None:
    """
    Sets the 'active' column value for a row in SQL table by listing id.

    :param listing_id: id of the listing that is going to be changed.
    :param table: Listing table name.
    :param connection: SLQ connection object.
    :param activate: Set to True if a listing needs to be activated instead of deactivated.
    :return: None
    """
    if activate:
        update_table_command = f"UPDATE {table} SET active = {int(activate)} WHERE id = {listing_id}"
    else:
        update_table_command = f"UPDATE {table} SET active = {int(activate)}, " \
                               f"date_unlisted = {round(time.time(), 0)} WHERE id = {listing_id}"

    sql_cursor = connection.cursor()
    sql_cursor.execute(update_table_command)
    return
