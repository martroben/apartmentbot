
import sqlite3
from data_processing import Listing


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


listing_columns = [key + " " + get_sqlite_data_type(value) for key, value in vars(Listing()).items()]
listing_columns_string = ",\n".join(listing_columns)
sql_create_listing_table = "CREATE TABLE listing (\n" + listing_columns_string + "\n)"

print(sql_create_listing_table)