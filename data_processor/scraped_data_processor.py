
# standard
from datetime import datetime
import logging
import os
import random
import re
import shutil
import sqlite3
import sys

# external
from dotenv import dotenv_values

# local
sys.path.append("/home/mart/Python/apartmentbot/data_processor")
import sqlite_operations
import c24_data_operations
from data_classes import Listing


#############
# Functions #
#############


def validate_scraped_data(listings: (set[Listing], list[Listing])) -> bool:
    """
    Validate that a random sample of listings has address information.

    :param listings: A set of listings
    :return: True if any listings in a random sample have address information. False otherwise
    """
    sample_size = 1 + int(0.02 * len(listings))
    address_sample = [len(listing.address) != 0 for listing in random.sample(list(listings), sample_size)]
    return any(address_sample)


def archive_scraped_data_file(file_path: str, archive_dir_path: str, not_used: bool = False) -> None:
    """
    Moves file to another directory and optionally add "NOT_USED_" to file name.
    Creates destination directory if it doesn't exist.

    :param file_path: Source file path
    :param archive_dir_path: Destination directory path
    :param not_used: Add "NOT_USED_" to filename if True
    :return: None
    """
    if not os.path.exists(archive_dir_path):
        os.makedirs(archive_dir_path)
    # Add NOT_USED_ to filename if input parameter not_used is True
    if not_used:
        destination_path = os.path.join(archive_dir_path, f"NOT_USED_{os.path.basename(file_path)}")
    else:
        destination_path = archive_dir_path
    shutil.move(file_path, destination_path)


###########
# Execute #
###########

env_file_path = ".env"
env_variables = dotenv_values(env_file_path)

os.environ["LOG_DIR_PATH"] = "/home/mart/Python/apartmentbot/log"
os.environ["C24_INDICATOR"] = env_variables["C24_INDICATOR"]
os.environ["SQL_DATABASE_PATH"] = "/home/mart/Python/apartmentbot/sql.db"
os.environ["SQL_LISTINGS_TABLE_NAME"] = env_variables["SQL_LISTINGS_TABLE_NAME"]
os.environ["SCRAPED_PAGES_NEW_PATH"] = "/home/mart/Python/apartmentbot/log/scraped_pages/new"
os.environ["SCRAPED_PAGES_PROCESSED_PATH"] = "/home/mart/Python/apartmentbot/log/scraped_pages/processed"

if __name__ == "__main__":
    # Set logging
    LOG_DIR_PATH = os.environ["LOG_DIR_PATH"]
    if not os.path.exists(LOG_DIR_PATH):
        os.makedirs(LOG_DIR_PATH)

    logging.basicConfig(
        # stream=sys.stdout,
        filename=f"{LOG_DIR_PATH}/{datetime.today().strftime('%Y_%m')}.log",
        format="{asctime}|{funcName}|{levelname}:{message}",
        style="{",
        level=logging.INFO)

    logging.info(f"\n\n\n{'-*-'*10} SCRAPED DATA PROCESSOR STARTED {'-*-'*10}\n")

    # Load environmental variables
    try:
        C24_INDICATOR = os.environ["C24_INDICATOR"]
        SQL_DATABASE_PATH = os.environ["SQL_DATABASE_PATH"]
        SQL_LISTINGS_TABLE_NAME = os.environ["SQL_LISTINGS_TABLE_NAME"]
        SCRAPED_PAGES_NEW_PATH = os.environ["SCRAPED_PAGES_NEW_PATH"]
        SCRAPED_PAGES_PROCESSED_PATH = os.environ["SCRAPED_PAGES_PROCESSED_PATH"]
    except KeyError as error:
        log_string = f"While loading environmental variables " \
                     f"{type(error).__name__} occurred: {error}. Exiting!"
        logging.error(log_string)
        exit(1)

    # Index scraped data files
    new_scraped_data_file_paths = [os.path.join(SCRAPED_PAGES_NEW_PATH, filename)
                                   for filename in os.listdir(SCRAPED_PAGES_NEW_PATH)]

    if not new_scraped_data_file_paths:
        logging.warning(f"No scraped data files found in {SCRAPED_PAGES_NEW_PATH}. Exiting!")
        exit(0)

    for scraped_data_file_path in new_scraped_data_file_paths:

        logging.info(f"Processing scraped data file {scraped_data_file_path}.")
        scraped_listings = set()

        # Handle c24 scraped data file
        if re.search(rf"{C24_INDICATOR}$", scraped_data_file_path):  # if file name ends with "_c24"
            logging.info(f"Detected c24 indicator, reading data.")
            try:
                json_data = c24_data_operations.get_json_data(scraped_data_file_path)
                if not json_data:       # If data can't be parsed, archive file and continue
                    archive_scraped_data_file(scraped_data_file_path, SCRAPED_PAGES_PROCESSED_PATH, not_used=True)
                    continue
                for listing_json in json_data:
                    scraped_listings.add(c24_data_operations.get_listing(listing_json))
            except Exception as exception:
                log_string = f"While converting c24 scraped data to Listing, " \
                             f"{type(exception).__name__} occurred: {exception}."
                logging.exception(log_string)
                del log_string

        # Validate processed data
        if not validate_scraped_data(scraped_listings):
            log_string = f"Couldn't validate scraped data from file {scraped_data_file_path}. " \
                         f"Archiving the file without using the data."
            logging.warning(log_string)
            del log_string
            archive_scraped_data_file(scraped_data_file_path, SCRAPED_PAGES_PROCESSED_PATH, not_used=True)
            continue

        # Connect to sql
        if not os.path.exists(os.path.dirname(SQL_DATABASE_PATH)):
            os.makedirs(os.path.dirname(SQL_DATABASE_PATH))
        try:
            logging.info(f"Establishing sql connection to {SQL_DATABASE_PATH}")
            sql_connection = sqlite3.connect(SQL_DATABASE_PATH)
            if not sqlite_operations.table_exists(SQL_LISTINGS_TABLE_NAME, sql_connection):
                logging.info(f"No sql table by the name {SQL_LISTINGS_TABLE_NAME}. Creating.")
                sqlite_operations.create_listings_table(SQL_LISTINGS_TABLE_NAME, sql_connection)

            # Get existing active listings from sql
            logging.info("Getting existing active listings from sql.")
            sql_active_listings = sqlite_operations.read_data(
                table=SQL_LISTINGS_TABLE_NAME,
                connection=sql_connection,
                where="active = 1")

            # Insert new listings to sql
            existing_active_listings = [Listing().make_from_dict(sql_listing) for sql_listing in sql_active_listings]
            logging.info(f"{len(existing_active_listings)} existing active listings loaded from sql.")

            new_listings = {listing for listing in scraped_listings if listing not in existing_active_listings}
            logging.info(f"{len(new_listings)} new unknown listings found from scraped data. Inserting to sql.")
            for listing in new_listings:
                sqlite_operations.insert_listing(
                    listing=listing,
                    table=SQL_LISTINGS_TABLE_NAME,
                    connection=sql_connection)

            # Set removed listings inactive in sql
            unlisted_listings = [listing for listing in existing_active_listings if listing not in scraped_listings]
            logging.info(f"{len(unlisted_listings)} existing active listings are no longer present in scraped data. "
                         f"Setting these listings to inactive in sql.")
            for listing in unlisted_listings:
                sqlite_operations.deactivate_listing(
                    table=SQL_LISTINGS_TABLE_NAME,
                    connection=sql_connection,
                    **{variable: listing.__getattribute__(variable) for variable in listing.__eq_variables__})
                sqlite_operations.set_unlisting_date(
                    table=SQL_LISTINGS_TABLE_NAME,
                    connection=sql_connection,
                    **{variable: listing.__getattribute__(variable) for variable in listing.__eq_variables__})
            sql_connection.commit()

            logging.info(f"Processing file {scraped_data_file_path} is completed. Archiving file.")
            archive_scraped_data_file(scraped_data_file_path, SCRAPED_PAGES_PROCESSED_PATH)

        except Exception as exception:
            log_string = f"While performing sql operations on {SQL_DATABASE_PATH}, " \
                         f"{type(exception).__name__} occurred: {exception}."
            logging.exception(log_string)
            del log_string
