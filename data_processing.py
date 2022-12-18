"""
Keys of processed data dictionaries:
id: str
portal: str [c24, kv] - important for defining save directories etc.
active: int
url: str
image_url: str
address: str
city: str
street: str
house_number: str
apartment_number: str
n_rooms: int
area_m2: float
price: float
construction_year: int
date_listed: float (epoch time)
date_scraped: float (epoch time)
date_unlisted: float (epoch time)

Imported modules:
csv
re
bs4.element
time
timegm from calendar
"""
import config

import csv
import re
import bs4.element
import time
from calendar import timegm
import logging
import hashlib


def get_class_variables(class_object: (object, str)) -> dict:
    """
    Helper function to get class variables (without dunder variables and functions.)

    :param class_object: Class object or object name string
    :return: dict with names and values of class variables
    """
    if isinstance(class_object, str):
        class_object = eval(class_object)
    return {key: value for key, value in class_object.__dict__.items() if not key.startswith("__") and not callable(value)}


class Listing:

    id = str()
    portal = str()
    active = int()
    url = str()
    image_url = str()
    address = str()
    city = str()
    street = str()
    house_number = str()
    apartment_number = str()
    n_rooms = int()
    area_m2 = float()
    price_eur = float()
    construction_year = int()
    date_listed = float()
    date_scraped = float()
    date_unlisted = float()

    def __setattr__(self, key, value):
        """Check if variable is allowed and typecast it to the correct type."""
        if key in self.__class__.__dict__:
            value = type(self.__class__.__dict__[key])(value)
            super().__setattr__(key, value)
        else:
            try:
                raise UserWarning(f"'{key}' is not a variable of class {type(self).__name__}. Value not inserted!")
            except UserWarning as warning:
                log_string = f"While inserting '{key}={value}': {warning}"
                logging.warning(log_string)

    def __init__(self):
        # Copy class variable default values to instance variables (so that vars() would work).
        class_variables = get_class_variables(self.__class__)
        for key, value in class_variables.items():
            setattr(self, key, value)

    def make_from_dict(self, listing_dict):
        """Set values of variables from a dict"""
        for key, value in listing_dict.items():
            setattr(self, key, value)
        return self

    def __str__(self):
        return f"{self.id} | {self.address}"

    def __eq__(self, other):
        """
        If the compared to another Listing object, first compares id-s.
        If these do not match, compares portal, address, area_m2 and price_eur variables.
        """
        if isinstance(other, Listing):
            if self.id == other.id:
                return True
            variables_match = (self.portal, self.address, self.area_m2, self.price_eur) == \
                              (other.portal, other.address, other.area_m2, other.price_eur)
            return variables_match
        return NotImplemented


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


def combine_street_address(street: str, house_number: (str,int), apartment_number: (str,int)) -> str:
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


def generate_listing_id(listing: Listing) -> str:
    """
    Generates (hopefully unique) id based on listing address and area_m2

    :param listing: Listing object
    :return: 7-character ID starting with X
    """
    hash_length = 7
    hash_seed = f"{str(listing.area_m2)} {listing.address}"
    listing_hash = hashlib.shake_128(hash_seed.encode()).hexdigest(int(hash_length - 1 / 2))
    listing_id = f"X{listing_hash}".upper()
    return listing_id


def c24_get_listing_details(data: dict) -> Listing:
    """
    Extracts values from a single c24 website listing item.

    :param data: json dict from c24 API call
    :return: Listing with listing info
    """
    listing = Listing()
    listing.portal = config.C24_INDICATOR
    listing.active = 1

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
        url_location_indication = "-".join([normalize_string(string) for string in url_location_components]).replace(" ", "-")
    except Exception as err:
        logging.warning(f"{type(err)} error occurred while trying to produce legit location indication for {str(listing)}: {err}")
        url_location_indication = ""
    listing.url = "/".join([url_base, url_type_indication, url_location_indication, data["friendly_id"]])

    # True image url from inspection:
    # https://c24ee.img-bcg.eu/object/11/1468/1096481468.jpg
    # It's the listing["main_image"]["url"] value with {fmt:em} value replaced with some number
    # It seems that {fmt:em} determines different sizes and crop formats for the image. Accepted values: 10-24
    # Using "11" as {fmt:em} value in this script
    image_url_fmt_em = "11"
    listing.image_url = data["main_image"]["url"].replace("{fmt:em}", image_url_fmt_em)

    # Combine address to single string
    apartment_number = data["address"]["apartment_number"]
    house_number = data["address"]["house_number"]
    street = data["address"]["street"]["name"]
    city = data["address"]["city"]["name"]
    parish = data["address"]["parish"]["name"]
    county = data["address"]["county"]["name"]
    street_house_apartment = combine_street_address(street, house_number, apartment_number)
    listing.address = f"{county}, {parish}, {city}, {street_house_apartment}"
    listing.city = city
    listing.street = street
    listing.house_number = house_number
    listing.apartment_number = apartment_number

    listing.n_rooms = int(data["room_count"])
    listing.area_m2 = float(data["property_size"])
    listing.price = float(data["price"])
    listing.construction_year = int(data["attributes"].get("construction_year", 0))
    # Using epoch time
    listing.date_listed = timegm(time.strptime(data["date_published"], "%Y-%m-%dT%H:%M:%S%z"))
    listing.date_scraped = round(time.time(), 0)

    # Get id
    try:
        listing.id = data["id"]
        if listing.id == "":
            listing.id = generate_listing_id(listing)
            raise UserWarning(f"Couldn't get id from scraped data. Assigned automatic id.")
    except UserWarning as warning:
        log_string = f"While trying to get id for {str(listing)}: {warning}"
        logging.warning(log_string)
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get id for {str(listing)}: {exception}"
        logging.exception(log_string)

    return listing


def kv_get_listing_details(data: bs4.element.Tag) -> Listing:
    """
    Extracts values from a single kv website listing item.

    :param data: bs4.element.Tag object - listing item (tag article) scraped from kv website
    :return: Listing with listing info
    """
    area_pattern = re.compile(r"\d+\.?\d*")  # Get only the numeric part of the area
    price_pattern = re.compile(r"\d+")  # Get only the numeric parts of the price, join findall results

    listing = Listing()

    listing.portal = config.KV_INDICATOR
    listing.active = 1

    # Get url
    try:
        listing.url = config.KV_BASE_URL + data["data-object-url"]
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get url for {str(listing)}: {exception}"
        logging.exception(log_string)

    # Get image url
    try:
        media = data.find("div", {"class": "media"})
        listing.image_url = media.find("img")["data-src"]
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get image url for {str(listing)}: {exception}"
        logging.exception(log_string)

    # Get address
    try:
        address_object = data.find("div", {"class": "description"})
        address_string = address_object.find_all("a", class_=False)
        listing.address = address_string[0].string.strip()
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get address for {str(listing)}: {exception}"
        logging.exception(log_string)

    parsed_address = kv_parse_address(listing.address)
    listing.city = parsed_address["city"]
    listing.street = parsed_address["street"]
    listing.house_number = parsed_address["house_number"]
    listing.apartment_number = parsed_address["apartment_number"]

    # Get n_rooms
    try:
        n_rooms = data.find("div", {"class": "rooms"})
        listing.n_rooms = int(n_rooms.string.strip())
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get the number of rooms for {str(listing)}: {exception}"
        logging.exception(log_string)

    # Get area
    try:
        area_m2 = data.find("div", {"class": "area"})
        area_numeric = area_pattern.search(area_m2.string).group()
        listing.area_m2 = float(area_numeric)
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get area (m2) for {str(listing)}: {exception}"
        logging.warning(log_string)

    # Get price
    try:
        price_object = data.find("div", {"class": "price"})
        for child in price_object.children:
            # Extract the element that has no tag and is not a single character
            if isinstance(child, bs4.element.NavigableString) and len(child.text) > 1:
                price_string = "".join(price_pattern.findall(child.text))
                listing.price_eur = float(price_string)
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get price for {str(listing)}: {exception}"
        logging.exception(log_string)

    # Get construction year
    construction_year_pattern = re.compile(r"ehitusaasta\s*(\d{4})")
    object_excerpts = data.find_all("p", {"class": "object-excerpt"})
    construction_year = [construction_year_pattern.findall(excerpt.text) for excerpt in object_excerpts]
    construction_year = [int(item[0]) for item in construction_year if len(item) != 0]
    listing.construction_year = construction_year[0] if len(construction_year) != 0 else int()

    listing.date_scraped = round(time.time(), 0)

    # Get id
    try:
        listing.id = data["data-object-id"]
        if listing.id == "":
            listing.id = generate_listing_id(listing)
            raise UserWarning(f"Couldn't get id from scraped data. Assigned automatic id.")
    except UserWarning as warning:
        log_string = f"While trying to get id for {str(listing)}: {warning}"
        logging.warning(log_string)
    except Exception as exception:
        log_string = f"{type(exception).__name__} occurred " + \
                     f"while trying to get id for {str(listing)}: {exception}"
        logging.exception(log_string)

    return listing


def separate_listings_by_portal(listings: list) -> dict:
    """
    Separates a list of listings to a dict where keys are portal indicators and
    values are listings only for one portal.

    :param listings: List of listings (dicts)
    :return: Dict of listings
    """
    listings_by_portal = {}
    for listing in listings:
        if listing["portal"] not in listings_by_portal.keys():
            listings_by_portal[listing["portal"]] = []
        listings_by_portal[listing["portal"]] += [listing]

    return listings_by_portal


def kv_parse_address(address: str) -> dict:
    """
    Extracts street, house and apartment from the full address string and parses them in a dict.

    :param address: Address string scraped from kv.
    :return: A dict with keys "city", "street", "house_number" and "apartment_number".
    Keys with missing values are assigned empty strings.
    """

    # Regex patterns
    city_pattern = re.compile(r"^\w+,\s*(\w+)\s*,")             # Part between first and second comma
    street_address_pattern = re.compile(r".*(?<!\d),(.+?)$")    # From last comma not preceded by number until end of line
    superfluous_comma_pattern = re.compile(r" ?, ?")            # Handle addresses like "Kalaranna 21, 23-49" (replace with "/")
    street_abbreviation_pattern = re.compile(r" tn")            # Remove "tn" after street name
    apartment_number_pattern = re.compile(r"-(\w+)$")           # Extract apartment number: from last "-" to end of line
    apartment_cleanup_pattern = re.compile(r"-[^-]{0,3}$")      # Remove apartment: 0-3 non-"-" characters after last "-" (e.g. Kalaranna 8/2-. or Mootori 7/3-38)
    house_number_pattern = re.compile(r" ([\w/]+)$")            # Alphanumeric or "/" from last space to end of line

    # Extract city from the full address string
    city = city_pattern.findall(address)
    if len(city) != 1:
        city = [""]
    city = city[-1]

    # Extract street, house, apartment from the full address string
    street_address = street_address_pattern.findall(address)
    if len(street_address) != 1:
        street_address = [""]
    street_address = superfluous_comma_pattern.sub("/", street_address[-1])
    street_address = street_abbreviation_pattern.sub("", street_address).strip()

    # Extract apartment number
    apartment_number = apartment_number_pattern.findall(street_address)
    if len(apartment_number) != 1:
        apartment_number = [""]
    apartment_number = apartment_number[-1]

    # Extract house number
    street_address_truncated = apartment_cleanup_pattern.sub("", street_address)
    house_number = house_number_pattern.findall(street_address_truncated)
    if len(house_number) != 1:
        house_number = [""]
    house_number = house_number[-1]

    # Extract street name
    street_name = house_number_pattern.sub("", street_address_truncated)
    if len(street_name) == 0:
        street_name = ""

    address_dict = {
        "city": city,
        "street": street_name,
        "house_number": house_number,
        "apartment_number": apartment_number}

    # Print warning if info parsed from address string is missing too many fields
    try:
        missing_keys = [key for key, value in address_dict.items() if value == ""]
        if len(missing_keys) > 1:
            raise UserWarning(f"Couldn't parse address elements: {', '.join(missing_keys)}")
    except UserWarning as warning:
        logging.warning(f"{type(warning).__name__} occurred while trying to parse address '{address}': {warning}.")

    return address_dict
