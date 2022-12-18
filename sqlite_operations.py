
import sqlite3
from data_processing import Listing
import config
import logging
import os
import re
from bs4 import BeautifulSoup
import data_processing


def log_exceptions(function):
    """
    Decorator function to log exceptions occurring in a function.
    """
    def inner_function(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as exception:
            log_string = f"In function {function.__name__}, {type(exception).__name__} exception occurred: {exception}"
            print(log_string)
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
def sql_table_exists(name: str, connection: sqlite3.Connection) -> bool:
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
def sql_create_listing_table(table: str, connection: sqlite3.Connection) -> None:
    """
    Creates table for listings to SQLite, using config.SQL_LISTING_TABLE_NAME as table name

    :param table: SQL listings table name
    :param connection: SQL connection object.
    :return: None
    """
    listing_columns_types = [key + " " + get_sqlite_data_type(value) for key, value in vars(Listing()).items()]
    listing_columns_types_string = ",\n\t".join(listing_columns_types)
    create_table_command = f"CREATE TABLE {table} (\n\t{listing_columns_types_string}\n);"

    sql_cursor = connection.cursor()
    sql_cursor.execute(create_table_command)
    return


def sql_insert_listing(listing: Listing, table: str, connection: sqlite3.Connection) -> None:
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
        connection.commit()
    except sqlite3.OperationalError as sql_error:
        log_string = f"In function {sql_insert_listing.__name__}, {type(sql_error).__name__} error occurred " + \
                     f"with listing '{listing.address}': {sql_error}"
        print(log_string)
    return


def sql_read_data(table: str, connection: sqlite3.Connection, where: (None, str) = None) -> list[dict]:
    """
    Get data from a SQL table.

    :param table: SQL table name.
    :param connection: SQL connection.
    :param where: SQL WHERE filter string
    :return: A list of column_name:value dicts.
    """
    get_data_command = f"SELECT * FROM {table};" if where is None else f"SELECT * FROM {table} WHERE {where};"
    sql_cursor = connection.cursor()
    data = sql_cursor.execute(get_data_command).fetchall()
    data_column_names = [item[0] for item in sql_cursor.execute(get_data_command).description]

    data_rows = list()
    for row in data:
        data_row = {key: value for key, value in zip(data_column_names, row)}
        data_rows += [data_row]

    return data_rows


with open(f"{os.getcwd()}/sample_response.txt", "r") as sample_response:
    response = sample_response.read()

kv_listings = []
scraper = BeautifulSoup(response, "html.parser")

# Extract the number of total listings from first page
n_total_listings_pattern = re.compile(r'<span\s*class="large\s*stronger">.*?(\d+)\s*</span>')
n_total_listings_match = n_total_listings_pattern.search(response)
n_total_listings = int(n_total_listings_match.group(1)) if n_total_listings_match is not None else None

kv_listings_raw = scraper.find_all("article")
kv_listings += [data_processing.kv_get_listing_details(item) for item in kv_listings_raw]

sql_connection = sqlite3.connect(config.SQL_DATABASE_PATH)
if not sql_table_exists(config.SQL_LISTING_TABLE_NAME, sql_connection):
    sql_create_listing_table(config.SQL_LISTING_TABLE_NAME, sql_connection)

for listing in kv_listings:
    sql_insert_listing(
        listing=listing,
        table=config.SQL_LISTING_TABLE_NAME,
        connection=sql_connection)

sql_existing_active_listings = sql_read_data(
    table=config.SQL_LISTING_TABLE_NAME,
    connection=sql_connection,
    where="active = 1")

existing_active_listings = [Listing().make_from_dict(listing_dict) for listing_dict in sql_existing_active_listings]

for listing in existing_active_listings:
    print(listing)
