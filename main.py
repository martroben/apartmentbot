import config
import portal_requests
import data_processing
import file_mgmt
import tor_operations

from datetime import date
import csv
import os.path
from bs4 import BeautifulSoup
import logging
import time

#################
# Start logging #
#################

if not os.path.exists(config.LOG_FOLDER):
    os.makedirs(config.LOG_FOLDER)

logging.basicConfig(
    filename= f"{config.LOG_FOLDER}/{date.today().strftime('%Y-%m-%d')}.log",
    format="{asctime}|{funcName}|{levelname}:{message}",
    style="{",
    level=logging.DEBUG)

logging.info("Apartment bot start!")


#############
# Setup tor #
#############

tor_operations.setup_tor()
print(config.TOR_CONTROL_PORT_PASSWORD)


###############
# Scrape data #
###############

# Process c24 data
c24_response = portal_requests.c24_request(3)
c24_listings = [data_processing.c24_get_listing_details(item) for item in c24_response.json()]

# Process kv data
kv_response = portal_requests.kv_request(3)
kv_listings = list()
for page in kv_response:
    scraper = BeautifulSoup(page.content, "html.parser")
    kv_listings_raw = scraper.find_all("article")
    kv_listings += [data_processing.kv_get_listing_details(item) for item in kv_listings_raw]

responses = {config.C24_INDICATOR: c24_response, config.KV_INDICATOR: kv_response}
scraped_listings = c24_listings + kv_listings


#####################
# Save data to disk #
#####################

# Create necessary folder structure in storage location
for portal_dir in responses.keys():
    portal_dir_path = os.path.join(config.STORAGE_DIR, portal_dir)
    file_mgmt.check_dir_structure(portal_dir_path)

# Save request data
for portal_dir, response in responses.items():
    portal_archive_dir_path = os.path.join(config.STORAGE_DIR, portal_dir, config.REQUESTS_ARCHIVE_DIR)
    file_mgmt.save_requests_to_txt(response, portal_archive_dir_path)

# Check maximum allowed size and cull request archives if necessary
for portal_dir in responses.keys():
    portal_archive_dir_path = os.path.join(config.STORAGE_DIR, portal_dir, config.REQUESTS_ARCHIVE_DIR)
    while file_mgmt.get_dir_size_mb(portal_archive_dir_path) > config.MAX_REQUEST_ARCHIVE_SIZE_MB:
        file_mgmt.remove_oldest_file(portal_archive_dir_path)


##############################
# Compare with existing data #
##############################

active_listings_paths = []
for portal_dir in responses.keys():
    portal_active_listings_path = os.path.join(config.STORAGE_DIR, portal_dir, config.ACTIVE_LISTINGS_FILENAME)
    active_listings_paths.append(portal_active_listings_path)

active_listings = []
for csv_path in active_listings_paths:
    if os.path.exists(csv_path):
        with open(csv_path, "r") as csv_file:
            reader = csv.DictReader(csv_file)
            active_listings += list(reader)

active_listings_ids = [listing["id"] for listing in active_listings]
scraped_listings_ids = [listing["id"] for listing in scraped_listings]
expired_listings = [listing for listing in active_listings if listing["id"] not in scraped_listings_ids]
# For e-mail
new_listings = [listing for listing in scraped_listings if listing["id"] not in active_listings_ids]
new_listings_ids = [listing["id"] for listing in new_listings]

# Assign today as date_added to listings that don't have that parameter (date_added = 0)
for listing in scraped_listings:
    if listing["date_added"] == 0 and listing["id"] in new_listings_ids:
        listing["date_added"] = time.time()

# Dicts separated by portal name
scraped_listings_by_portal = data_processing.separate_listings_by_portal(scraped_listings)
expired_listings_by_portal = data_processing.separate_listings_by_portal(expired_listings)


##############################
# Save updated listings data #
##############################

# Save active listings
for portal_dir, data in scraped_listings_by_portal.items():
    active_listings_paths = os.path.join(config.STORAGE_DIR, portal_dir, config.ACTIVE_LISTINGS_FILENAME)
    file_mgmt.write_data_csv(data, active_listings_paths, replace=True)

# Save expired listings
for portal_dir, data in expired_listings_by_portal.items():
    expired_listings_paths = os.path.join(config.STORAGE_DIR, portal_dir, config.EXPIRED_LISTINGS_FILENAME)
    file_mgmt.write_data_csv(data, expired_listings_paths)


# TO DO
# QUERY_INPUT object to portal requests
# compress request archives
# logging system
