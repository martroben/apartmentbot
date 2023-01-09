
import os
import random
import re
import logging
import sqlite3
import shutil
from datetime import datetime
import sqlite_operations

from data_classes import Listing
import c24_data_operations


def get_unique_id_listings(listings: (list[Listing], set[Listing])) -> set[Listing]:
    """
    Check input for Listings with identical id-s. Drop the one that has earlier date_listed parameter.
    :param listings: Set of Listing objects
    :return: Set of Listing objects with unique id-s.
    """
    unique_id_listings = dict()
    for listing in listings:
        if listing.id in unique_id_listings and unique_id_listings[listing.id].date_listed > listing.date_listed:
            continue
        unique_id_listings[listing.id] = listing
    return {listing for listing in unique_id_listings.values()}


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


os.environ["LOG_DIR_PATH"] = "/home/mart/Python/apartmentbot/log"
os.environ["C24_INDICATOR"] = "c24"
os.environ["SQL_DATABASE_PATH"] = ":memory:"
os.environ["SQL_LISTINGS_TABLE_NAME"] = "listings"
os.environ["NEW_SCRAPED_DATA_DIR"] = "./log/scraped_pages/new"
os.environ["ARCHIVED_SCRAPED_DATA_DIR"] = "./log/scraped_pages/archived"

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
    # Mandatory
    C24_INDICATOR = os.environ["C24_INDICATOR"]
    SQL_DATABASE_PATH = os.environ["SQL_DATABASE_PATH"]
    SQL_LISTINGS_TABLE_NAME = os.environ["SQL_LISTINGS_TABLE_NAME"]
    NEW_SCRAPED_DATA_DIR = os.environ["NEW_SCRAPED_DATA_DIR"]
    ARCHIVED_SCRAPED_DATA_DIR = os.environ["ARCHIVED_SCRAPED_DATA_DIR"]
except KeyError as error:
    log_string = f"While loading environmental variables " \
                 f"{type(error).__name__} occurred: {error}. Exiting!"
    logging.error(log_string)
    exit(1)


new_scraped_data_file_paths = [os.path.join(NEW_SCRAPED_DATA_DIR, filename)
                               for filename in os.listdir(NEW_SCRAPED_DATA_DIR)]

sql_connection = sqlite3.connect(SQL_DATABASE_PATH)

for scraped_data_file_path in new_scraped_data_file_paths:
    logging.info(f"Processing scraped data file {scraped_data_file_path}.")
    scraped_listings = set()
    if re.search(rf"{C24_INDICATOR}$", scraped_data_file_path):  # if file name ends with "_c24"
        logging.info(f"Detected c24 indicator, reading data.")
        try:
            json_data = c24_data_operations.get_json_data(scraped_data_file_path)
            for listing_json in json_data:
                scraped_listings.add(c24_data_operations.get_listing(listing_json))
        except Exception as exception:
            log_string = f"While converting c24 scraped data to Listing, " \
                         f"{type(exception).__name__} occurred: {exception}."
            logging.exception(log_string)
            del log_string

    if not validate_scraped_data(scraped_listings):
        log_string = f"Couldn't validate scraped data from file {scraped_data_file_path}. " \
                     f"Archiving the file without using the data."
        logging.warning(log_string)
        del log_string
        archive_scraped_data_file(scraped_data_file_path, ARCHIVED_SCRAPED_DATA_DIR, not_used=True)
        continue

    try:
        logging.info(f"Establishing sql connection to {SQL_DATABASE_PATH}")
        ##### sql_connection = sqlite3.connect(SQL_DATABASE_PATH)
        if not sqlite_operations.table_exists(SQL_LISTINGS_TABLE_NAME, sql_connection):
            logging.info(f"No sql table by the name {SQL_LISTINGS_TABLE_NAME}. Creating.")
            sqlite_operations.create_listings_table(SQL_LISTINGS_TABLE_NAME, sql_connection)

        logging.info("Getting existing active listings from sql.")
        sql_active_listings = sqlite_operations.read_data(
            table=SQL_LISTINGS_TABLE_NAME,
            connection=sql_connection,
            where="active = 0")

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

        # Set removed listings to inactive
        ###### Can't do it by id only, otherwise active listings with same id will also be inactivated
        unlisted_listings_ids = [listing.id for listing in existing_active_listings if listing not in scraped_listings]
        logging.info(f"{len(unlisted_listings_ids)} existing active listings are no longer present in scraped data. "
                     f"Setting these listings to inactive in sql.")
        for listing_id in unlisted_listings_ids:
            sqlite_operations.deactivate_id(
                listing_id=listing_id,
                table=SQL_LISTINGS_TABLE_NAME,
                connection=sql_connection)

        sql_connection.commit()

        logging.info(f"Processing file {scraped_data_file_path} is completed. Archiving file.")
        archive_scraped_data_file(scraped_data_file_path, ARCHIVED_SCRAPED_DATA_DIR)

    except Exception as exception:
        log_string = f"While performing sql operations on {SQL_DATABASE_PATH}, " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)
        del log_string
