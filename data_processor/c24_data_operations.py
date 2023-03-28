
import os
import re
import time
import json
import parsel
import logging
from calendar import timegm

from data_classes import Listing


def get_json_data(file_path: str) -> list[dict]:
    """
    Loads data from a c24 exported page source file and extracts the json component.

    :param file_path: c24 scraped data export file path.
    :return: A list of listings in the form of json dicts
    """
    c24_page_json_content_xpath = "//pre/text()"

    with open(file_path) as exported_page:
        page = exported_page.readline()
    selector = parsel.Selector(text=page)
    page_json_content = selector.xpath(c24_page_json_content_xpath).get()
    page_json = json.loads(page_json_content)
    return page_json


def normalize_string(string: str) -> str:
    """
    Converts string to lowercase and replaces umlauts
    E.g. Ülo õe äi -> ulo oe ai
    """
    replacements = [
        ("ä", "a"),
        ("õ", "o"),
        ("ü", "u"),
        ("ö", "u")]
    for replacement in replacements:
        string = re.sub(replacement[0], replacement[1], string, flags=re.IGNORECASE)
    return string.lower()


def combine_street_address(street: str, house_number: (str, int), apartment_number: (str, int)) -> str:
    """
    Combines street name, house number and apartment number to a standard street address string.
    Handles missing elements (empty strings) gracefully.

    :param street:
    :param house_number:
    :param apartment_number:
    :return: String with input elements combined to an address.
    """
    house_apartment = "-".join([element for element in [house_number, apartment_number] if element not in [None, ""]])
    street_house_apartment = " ".join([element for element in [street, house_apartment] if element not in [None, ""]])
    return street_house_apartment


def get_listing(data: dict) -> Listing:
    """
    Extracts values from a c24 scraped page json.

    :param data: json dict from c24 scraped page
    :return: Listing with listing info
    """
    listing = Listing()
    listing.portal = os.environ["C24_INDICATOR"]
    listing.active = 1
    listing.reported = 0

    # Combine address to single string
    listing.apartment_number = data["address"]["apartment_number"]
    listing.house_number = data["address"]["house_number"]
    listing.street = data["address"]["street"]["name"]
    listing.city = data["address"]["city"]["name"]
    parish = data["address"]["parish"]["name"]
    county = data["address"]["county"]["name"]
    street_house_apartment = combine_street_address(listing.street, listing.house_number, listing.apartment_number)
    listing.address = ", ".join([element for element in [street_house_apartment, listing.city, parish, county]
                                 if element is not None])

    # True url example from inspection:
    # https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kopli-tn/2960653
    # url components:
    # https://www.city24.ee/real-estate/
    # + string-indicating-listing-type /
    # + string-indicating-listing-location /
    # + friendly_id
    # The indication strings can be anything (e.g. empty string),
    # nevertheless, the script will try to generate something legit-looking to fit in
    url_base = "https://www.city24.ee/real-estate"
    url_type_indication = "apartments-for-sale"
    try:
        url_location_components = [
            data["address"]["parish"]["name"],
            data["address"]["city"]["name"],
            data["address"]["street"]["name"]]
        # Replace umlauts and convert spaces to dashes
        url_location_components_normalized = [normalize_string(string) for string in url_location_components]
        url_location_indication = "-".join(url_location_components_normalized).replace(" ", "-")
    except Exception as exception:
        log_string = f"While trying to get direct url for {str(listing)}, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        del log_string
        url_location_indication = str()
    listing.url = "/".join([url_base, url_type_indication, url_location_indication, data["friendly_id"]])

    # True image url from inspection:
    # https://c24ee.img-bcg.eu/object/11/1468/1096481468.jpg
    # It's the listing["main_image"]["url"] value with {fmt:em} value replaced with some number
    # It seems that {fmt:em} determines different sizes and crop formats for the image. Accepted values: 10-24
    # Using "11" as {fmt:em} value in this script
    image_url_fmt_em = "11"
    listing.image_url = data["main_image"]["url"].replace("{fmt:em}", image_url_fmt_em)

    listing.n_rooms = int(data["room_count"])
    listing.area_m2 = float(data["property_size"])
    listing.price_eur = float(data["price"])
    listing.construction_year = int(data["attributes"].get("CONSTRUCTION_YEAR", 0))
    # Using epoch time
    listing.date_listed = timegm(time.strptime(data["date_published"], "%Y-%m-%dT%H:%M:%S%z"))
    listing.date_scraped = round(time.time(), 0)

    # Get id
    try:
        listing.id = data["id"]
        if listing.id == "":
            listing.assign_random_id()
            raise UserWarning(f"Couldn't get id from listing data. Assigned self-generated id.")
    except UserWarning as warning:
        log_string = f"While trying to get id for {str(listing)}: {warning}"
        logging.warning(log_string)
        del log_string
    except Exception as exception:
        log_string = f"While trying to get id for {str(listing)}, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        del log_string

    return listing


def detect_blocking(page: str, threshold: int = 3) -> bool:
    """
    Detect if scraper has been blocked by anti-scraping by keyphrases in page source ("captcha", "trouble").
    :param page: Scraped page source
    :return: True if there is a certain number of blocking indicators
    """
    blocking_indicators_pattern = re.compile(r"captcha|trouble")
    n_blocking_indicators = len(blocking_indicators_pattern.findall(page))
    return n_blocking_indicators >= threshold
