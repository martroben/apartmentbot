import requests
from requests import Request, Session
import random
import os

C24_BASE_URL = "https://m-api.city24.ee/et_EE/search/realties"
CONFIG_DIR_PATH = "/home/mart/Python/apartmentbot/config"
USER_AGENTS_FILE = "user_agents"
TOR_HOST = "127.0.0.1"
SOCKS_PORT = 9050
# Areas:
# 3166 - Põhja-Tallinn
# 1535 - Kristiine
C24_AREAS = "1535,3166"
C24_N_ROOMS = "3,4,5,6"


def get_c24_request(n_rooms: str, areas: str) -> requests.Request:
    """
    Query c24 for apartments.

    Example get request from inspection:
    https://m-api.city24.ee/et_EE/search/realties?address[cc]=1&address[city][]=3166&address[city][]=1535&tsType=sale&unitType=Apartment&roomCount=3&itemsPerPage=500&page=1

    page=1 by default.
    address[cc] doesn't seem to be necessary.
    The second brackets don't seem to be necessary in address[city][]. Used only if several areas are queried.
    Can add several address[city] parameters to query several areas.
    To query several room counts, use roomCount=3,4,5+

    :param n_rooms: Number of rooms to query for. Either int or list of ints.
    :return: requests.models.Response object.
    """
    c24_headers = {"User-Agent": USER_AGENT}
    c24_parameters = {
        "tsType": "sale",
        "unitType": "Apartment",
        "itemsPerPage": 500}

    # Handle several areas as input
    for i, area in enumerate(areas.split(",")):
        key_name = "address[city][" + str(i) + "]"
        c24_parameters[key_name] = area

    # Handle querying for several apartment sizes (number of rooms)
    n_rooms = [int(i) for i in n_rooms.split(",")]
    if any(i >= 5 for i in n_rooms):
        n_rooms_smaller = [str(i) for i in n_rooms if i < 5]
        c24_parameters["roomCount"] = ",".join(n_rooms_smaller + ["5+"])
    else:
        c24_parameters["roomCount"] = ",".join([str(i) for i in n_rooms])

    request = Request("GET", C24_BASE_URL, params=c24_parameters, headers=c24_headers)
    return request


# Get a random user agent
user_agents = list()
with open(os.path.join(CONFIG_DIR_PATH, USER_AGENTS_FILE), "r") as user_agents_file:
    for line in user_agents_file:
        user_agents += [line.strip()]
USER_AGENT = random.choice(user_agents)

tor_proxies = {
   "http": f"{TOR_HOST}:{SOCKS_PORT}",
   "https": f"{TOR_HOST}:{SOCKS_PORT}"}

c24_request = get_c24_request(n_rooms=C24_N_ROOMS, areas=C24_AREAS)

# c24_session = Session()
# c24_session.send(c24_request.prepare(), proxies=tor_proxies)
