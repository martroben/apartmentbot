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
date_added: float (epoch time)
date_scraped: float (epoch time)
date_removed: float (epoch time)

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


class Listing:
    def __init__(self):
        self.id: str = str()
        self.portal: str = str()
        self.active: int = int()
        self.url: str = str()
        self.image_url: str = str()
        self.address: str = str()
        self.city: str = str()
        self.street: str = str()
        self.house_number: str = str()
        self.apartment_number: str = str()
        self.n_rooms: int = int()
        self.area_m2: float = float()
        self.price: float = float()
        self.construction_year: int = int()
        self.date_added: float = float()
        self.date_scraped: float = float()
        self.date_removed: float = float()

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
    :return:
    """
    house_apartment = "-".join([element for element in [house_number, apartment_number] if element not in [None, ""]])
    street_house_apartment = " ".join([element for element in [street, house_apartment] if element not in [None, ""]])
    return street_house_apartment


def c24_get_listing_details(listing: dict) -> dict:
    """
    Extracts values from a single c24 website listing item.

    :param listing: json dict from c24 API call
    :return: dict with main listing info
    """
    details = dict()
    details["id"] = listing["id"]
    details["portal"] = config.C24_INDICATOR
    details["active"] = 1

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
            listing["address"]["parish"]["name"],
            listing["address"]["city"]["name"],
            listing["address"]["street"]["name"]]
        url_location_indication = "-".join([normalize_string(string) for string in url_location_components]).replace(" ", "-")
    except Exception as err:
        print(f"{type(err)} error occurred while trying to produce legit location indication for {str(details)}: {err}")
        url_location_indication = ""
    details["url"] = "/".join([url_base, url_type_indication, url_location_indication, listing["friendly_id"]])

    # True image url from inspection:
    # https://c24ee.img-bcg.eu/object/11/1468/1096481468.jpg
    # It's the listing["main_image"]["url"] value with {fmt:em} value replaced with some number
    # It seems that {fmt:em} determines different sizes and crop formats for the image. Accepted values: 10-24
    # Using "11" as {fmt:em} value in this script
    image_url_fmt_em = "11"
    details["image_url"] = listing["main_image"]["url"].replace("{fmt:em}", image_url_fmt_em)

    # Combine address to single string
    apartment_number = listing["address"]["apartment_number"]
    house_number = listing["address"]["house_number"]
    street = listing["address"]["street"]["name"]
    city = listing["address"]["city"]["name"]
    parish = listing["address"]["parish"]["name"]
    county = listing["address"]["county"]["name"]
    street_house_apartment = combine_street_address(street, house_number, apartment_number)
    details["address"] = f"{county}, {parish}, {city}, {street_house_apartment}"
    details["city"] = city
    details["street"] = street
    details["house_number"] = house_number
    details["apartment_number"] = apartment_number

    details["n_rooms"] = int(listing["room_count"])
    details["area_m2"] = float(listing["property_size"])
    details["price"] = float(listing["price"])
    details["construction_year"] = int(listing["attributes"].get("construction_year", 0))
    # Using epoch time
    details["date_added"] = timegm(time.strptime(listing["date_published"], "%Y-%m-%dT%H:%M:%S%z"))
    details["date_scraped"] = time.time()
    details["date_removed"] = float()

    return details


def kv_get_listing_details(listing: bs4.element.Tag) -> dict:
    """
    Extracts values from a single kv website listing item.

    :param listing: bs4.element.Tag object - listing item (tag article) scraped from kv website
    :return: dict with main listing info
    """
    area_pattern = re.compile(r"\d+\.?\d*")  # Get only the numeric part of the area
    price_pattern = re.compile(r"\d+")  # Get only the numeric parts of the price, join findall results

    details = {}
    # Get id
    try:
        details["id"] = listing["data-object-id"]
    except Exception as err:
        print(f"{type(err)} error occurred while trying to get id for {str(details)}: {err}")
        details["id"] = str()

    details["portal"] = config.KV_INDICATOR
    details["active"] = 1

    # Get url
    try:
        details["url"] = config.KV_BASE_URL + listing["data-object-url"]
    except Exception as err:
        print(f"{type(err)} error occurred while trying to get url for {str(details)}: {err}")
        details["url"] = str()

    # Get image url
    try:
        media = listing.find("div", {"class": "media"})
        details["image_url"] = media.find("img")["data-src"]
    except Exception as err:
        print(f"{type(err)} error occurred while trying to get image url for {str(details)}: {err}")
        details["image_url"] = str()

    # Get address
    try:
        address_object = listing.find("div", {"class": "description"})
        address_string = address_object.find_all("a", class_=False)
        details["address"] = address_string[0].string.strip()
    except Exception as err:
        print(f"{type(err)} error occurred while trying to get address for {str(details)}: {err}")
        details["address"] = str()

    parsed_address = kv_parse_address(details["address"])
    details["city"] = parsed_address["city"]
    details["street"] = parsed_address["street"]
    details["house_number"] = parsed_address["house_number"]
    details["apartment_number"] = parsed_address["apartment_number"]

    # Get n_rooms
    try:
        n_rooms = listing.find("div", {"class": "rooms"})
        details["n_rooms"] = int(n_rooms.string.strip())
    except Exception as err:
        print(f"{type(err)} error occurred while trying to get the number of rooms for {str(details)}: {err}")
        details["n_rooms"] = int()

    # Get area
    try:
        area_m2 = listing.find("div", {"class": "area"})
        area_numeric = area_pattern.search(area_m2.string).group()
        details["area_m2"] = float(area_numeric)
    except Exception as err:
        print(f"{type(err)} error occurred while trying to get area (m2) for {str(details)}: {err}")
        details["area_m2"] = float()

    # Get price
    try:
        price_object = listing.find("div", {"class": "price"})
        for child in price_object.children:
            # Extract the element that has no tag and is not a single character
            if isinstance(child, bs4.element.NavigableString) and len(child.text) > 1:
                price_string = "".join(price_pattern.findall(child.text))
                details["price_eur"] = float(price_string)
    except Exception as err:
        print(f"{type(err)} error occurred while trying to get the price for {str(details)}: {err}")
        details["price_eur"] = float()

    # Get construction year
    construction_year_pattern = re.compile(r"ehitusaasta\s*(\d{4})")
    object_excerpts = listing.find_all("p", {"class": "object-excerpt"})
    construction_year = [construction_year_pattern.findall(excerpt.text) for excerpt in object_excerpts]
    construction_year = [int(item[0]) for item in construction_year if len(item) != 0]
    details["construction_year"] = construction_year[0] if len(construction_year) != 0 else int()

    details["date_added"] = float()
    details["date_scraped"] = time.time()
    details["date_removed"] = float()

    return details


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
    Extract street, house and apartment from the full address string and parses them in a dict.

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
        print(f"WARNING, while trying to parse address '{address}': {warning}.")

    return address_dict