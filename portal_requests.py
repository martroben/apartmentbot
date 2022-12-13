import config

import requests
import re
from time import time, sleep


# Functions
def c24_request(n_rooms: int) -> requests.models.Response:
    """
    Query city24 for apartments.

    Example get request from inspection:
    https://m-api.city24.ee/et_EE/search/realties?address[cc]=1&address[city][]=3166&address[city][]=1535&tsType=sale&unitType=Apartment&roomCount=3&itemsPerPage=500&page=1

    page=1 by default.
    address[cc] doesn't seem to be necessary.
    The second brackets don't seem to be necessary in address[city][]. Used only if several areas are queried.
    Can add several address[city] parameters to query several areas.
    To query several room counts, use roomCount=3,4,5+

    :param n_rooms: Number of rooms to query for. Either int or list of ints.
    :return: requests.models.Response object from city24 request
    """

    # Areas:
    # 3166 - Põhja-Tallinn
    # 1535 - Kristiine
    areas = [3166]

    c24_headers = {"User-Agent": config.USER_AGENT_HEADER}
    c24_parameters = {
        "tsType": "sale",
        "unitType": "Apartment",
        "itemsPerPage": 500}

    # Handle several areas as input
    for i, area in enumerate(areas):
        key_name = "address[city][" + str(i) + "]"
        c24_parameters[key_name] = area

    # Handle querying for several apartment sizes (number of rooms)
    n_rooms = n_rooms if type(n_rooms) is list else [n_rooms]
    if any(i >= 5 for i in n_rooms):
        n_rooms_smaller = [str(i) for i in n_rooms if i < 5]
        c24_parameters["roomCount"] = ",".join(n_rooms_smaller + ["5+"])
    else:
        c24_parameters["roomCount"] = ",".join([str(i) for i in n_rooms])

    c24_response = requests.get(config.C24_BASE_URL, params=c24_parameters, headers=c24_headers)

    return c24_response


def kv_request(n_rooms: int) -> list:
    """
    Scrape kv.ee for apartments.

    Example get request from inspection:
    https://www2.kv.ee/et/search&deal_type=1&county=1&parish=1061&city[0]=1011&rooms_min=3&rooms_max=4&start=50

    For several areas: city[0] = id1, city[1] = id2
    For several sizes of apartments, set rooms_min and rooms_max parameters. Can be the same number.
    For subsequent pages after the first, use parameter start=50

    :param n_rooms: Number of rooms to query for. Either int or list of ints.
    :return: list of requests.models.Response objects.
    """

    # Areas:
    # 1011 - Põhja-Tallinn
    # 1004 - Kristiine
    areas = [1011]

    kv_headers = {"User-Agent": config.USER_AGENT_HEADER}
    kv_parameters = {
        "deal_type": 1,
        "county": 1,
        "parish": 1061}

    # Handle different apartment sizes (number of rooms) inputs
    n_rooms = n_rooms if type(n_rooms) is list else [n_rooms]
    kv_parameters["rooms_min"] = min(n_rooms)
    kv_parameters["rooms_max"] = max(n_rooms)

    # Handle several areas as input
    for i, area in enumerate(areas):
        key_name = "city[" + str(i) + "]"
        kv_parameters[key_name] = area

    # Handle pagination
    listing_counter = 0
    listing_pattern = re.compile(b"<article.*?</article")
    n_total_listings_pattern = re.compile(r'<span\s*class="large\s*stronger">.*?(\d+)\s*</span>')
    n_total_listings = None
    kv_responses = []
    while True:
        if listing_counter != 0:
            kv_parameters["start"] = listing_counter    # Avoid adding superfluous parameter to 1st page request

        kv_response = requests.get(config.KV_BASE_URL + "/et/search", headers=kv_headers, params=kv_parameters)
        n_listings = len(listing_pattern.findall(kv_response.content))

        if n_listings > 0:
            kv_responses += [kv_response]
            listing_counter += n_listings

            if n_total_listings is None:
                n_total_listings_match = n_total_listings_pattern.search(kv_response)
                n_total_listings = int(n_total_listings_match.group(1)) if n_total_listings_match is not None else None
            elif n_total_listings <= listing_counter:
                break                                   # Avoid superfluous last request
        else:
            break

        # sleep for a random time between 1-3 seconds before next request
        sleep(1 + 2 * (time() % 1))

    return kv_responses
