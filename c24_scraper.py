from collections.abc import Callable
import re
from requests import Request
import random
import os
import logging
from datetime import datetime
from time import sleep
from urllib.error import ContentTooShortError
import undetected_chromedriver as uc
import tor_operations
from functools import partial, wraps


os.environ["LOG_DIR_PATH"] = "/home/mart/Python/apartmentbot/log"
os.environ["SCRAPED_PAGES_NEW_PATH"] = "/home/mart/Python/apartmentbot/log/scraped_pages/new"
os.environ["TOR_HOST"] = "127.0.0.1"
os.environ["SOCKS_PORT"] = "9050"
os.environ["TOR_CONTROL_PORT"] = "9051"
os.environ["C24_BASE_URL"] = "https://m-api.city24.ee/et_EE/search/realties"
os.environ["C24_AREAS"] = "3166"  # 3166 - Põhja-Tallinn, 1535 - Kristiine
os.environ["C24_N_ROOMS"] = "3"
os.environ["C24_INDICATOR"] = "c24"
os.environ["IP_REPORTER_API_URL"] = "https://api.ipify.org"


def log_exceptions(context: str = ""):
    """
    Decorator function to log exceptions occurring in a function.
    Description of attempted actions can be supplied by a 'context' variable.
    """
    def decorator(function):
        def inner_function(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as exception:
                log_string = f"In function {function.__name__}, " \
                             f"{type(exception).__name__} exception occurred: {exception}" \
                             f"{bool(context)*f', while {context}'}."
                logging.exception(log_string)
        return inner_function
    return decorator


def get_human_wait_time():
    """
    Get a "human-like" wait time (for navigating to new page etc.)
    :return: Values between 5 and 20.
    """
    average_wait_time_sec = 3
    wait_time = random.expovariate(lambd=1/average_wait_time_sec)
    if wait_time < 3 or wait_time > 15:
        wait_time = get_human_wait_time()
    logging.info(f"Inserting wait time: {round(wait_time,2)} seconds.")
    return wait_time


def retry_function(function=None, *,
                   times: int = 3, interval_sec: (Callable, float) = 8.0,
                   exceptions: (Exception, tuple[Exception]) = Exception):
    """
    Retries the wrapped function. Meant to be used as a decorator.

    Optional parameters:
    times: int - The number of times to repeat the wrapped function (default: 3).
    exceptions: tuple[Exception] - Tuple of exceptions that trigger a retry attempt (default: Exception).
    interval_sec: float or a function with no arguments that returns a float
    How many seconds to wait between retry attempts (default: 8)
    """
    if function is None:
        return partial(retry_function, times=times, interval_sec=interval_sec, exceptions=exceptions)

    @wraps(function)
    def retry(*args, **kwargs):
        interval = interval_sec() if callable(interval_sec) else interval_sec
        attempt = 1
        while attempt <= times:
            try:
                return function(*args, **kwargs)
            except exceptions as exception:
                log_string = f"Retrying function {function.__name__} in {round(interval, 2)} seconds, " \
                             f"because {type(exception).__name__} exception occurred: {exception}\n" \
                             f"Attempt {attempt} of {times}."
                logging.exception(log_string)
                attempt += 1
                if attempt <= times:
                    sleep(interval)
    return retry


@retry_function(exceptions=ContentTooShortError)
def get_chrome_driver(options: uc.ChromeOptions = uc.ChromeOptions(),
                      chrome_driver_log_path: str =
                      os.path.join(os.environ["LOG_DIR_PATH"], "chromedriver.log")) -> uc.Chrome:
    """
    Start an uc chrome driver.

    :param options: chrome driver options object.
    :param chrome_driver_log_path: chrome driver.
    :return: a chrome driver object.
    """
    if not os.path.isdir(os.path.dirname(chrome_driver_log_path)):
        warning_string = f"Directory for logfile {chrome_driver_log_path} doesn't exist. " \
                         f"This may cause Chrome driver to quit unexpectedly."
        raise UserWarning(warning_string)
    driver = uc.Chrome(options=options, version_main=CHROME_VERSION, service_log_path=chrome_driver_log_path)
    driver.set_page_load_timeout(120)
    return driver


@retry_function(interval_sec=get_human_wait_time)
def uc_scrape_page(url: str, driver: uc.Chrome) -> str:
    """
    Scrape the target url with uc.

    :param url: Target url.
    :param driver: Chromedriver object.
    :return: Page source string.
    """
    driver.get(url)
    sleep(get_human_wait_time())
    scraped_data = driver.page_source
    driver.close()
    return scraped_data


def get_c24_request(n_rooms: str, areas: str) -> Request:
    """
    Get a request for c24.

    Example get request from inspection:
    https://m-api.city24.ee/et_EE/search/realties?address[cc]=1&address[city][]=3166&address[city][]=1535&tsType=sale&unitType=Apartment&roomCount=3&itemsPerPage=500&page=1

    page=1 by default.
    address[cc] doesn't seem to be necessary.
    The second brackets don't seem to be necessary in address[city][]. Used only if several areas are queried.
    Can add several address[city] parameters to query several areas.
    To query several room counts, use roomCount=3,4,5+

    :param n_rooms: Number of rooms to query for. String with comma separated values.
    :param areas: Area codes to query. String with comma separated values.
    :return: requests.models.Response object.
    """
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

    request = Request("GET", C24_BASE_URL, params=c24_parameters)
    return request


@log_exceptions(context="getting Chrome version from local file.")
def get_chrome_version() -> str:
    """
    Read Chrome version from the Last Version file in Chrome config files.
    :return: String of the major version (i.e. 106 from 106.0.5249.119-1)
    """
    chrome_version_file_path = os.path.join(os.path.expanduser("~"), ".config/google-chrome/Last Version")
    with open(chrome_version_file_path, "r") as version_file:
        version_string = version_file.readline()
        version_main_pattern = re.compile(r"^\d+")
        version_main = version_main_pattern.search(version_string)[0]
    return version_main


if __name__ == "__main__":

    # Set logging
    LOG_DIR_PATH = os.environ["LOG_DIR_PATH"]
    if not os.path.exists(LOG_DIR_PATH):
        os.makedirs(LOG_DIR_PATH)

    logging.basicConfig(
        filename=f"{LOG_DIR_PATH}/{datetime.today().strftime('%Y_%m')}.log",
        format="{asctime}|{funcName}|{levelname}:{message}",
        style="{",
        level=logging.INFO)

    logging.info("c24 scraper started")

    # Randomize scrape times
    # if random.uniform(0,1) < 0.7:
    #     logging.info("c24 scraper exited with no action (randomization)")
    #     exit()
    # random_sleep_time = random.uniform(0, 3500)
    # logging.info(f"c24 scraper sleeping for {round(random_sleep_time/60, 2)} minutes before action (randomization)")
    # sleep(random_sleep_time)

    # Load environmental variables
    try:
        # Mandatory
        SCRAPED_PAGES_NEW_PATH = os.environ["SCRAPED_PAGES_NEW_PATH"]
        TOR_HOST = os.environ["TOR_HOST"]
        SOCKS_PORT = os.environ["SOCKS_PORT"]
        C24_BASE_URL = os.environ["C24_BASE_URL"]
        C24_AREAS = os.environ["C24_AREAS"]
        C24_N_ROOMS = os.environ["C24_N_ROOMS"]
        C24_INDICATOR = os.environ["C24_INDICATOR"]
        # Optional
        IP_REPORTER_API_URL = os.environ.get("IP_REPORTER_API_URL")
        TOR_CONTROL_PORT = os.environ.get("TOR_CONTROL_PORT")
        TOR_CONTROL_PORT_PASSWORD = os.environ.get("TOR_CONTROL_PORT_PASSWORD")
    except KeyError as error:
        log_string = f"While load environmental variables " \
                     f"{type(error).__name__} occurred: {error}"
        logging.exception(log_string)
        exit(1)

    # Specify tor connection
    # Socket format: https://devpress.csdn.net/python/62fe30f8c6770329308047f0.html
    socks_socket = f"socks5://{TOR_HOST}:{SOCKS_PORT}"

    # Check if tor is up
    logging.info("Checking if tor service is up.")
    try:
        n_retries = 3
        for attempt in range(n_retries):
            if not tor_operations.is_up(TOR_HOST, SOCKS_PORT, IP_REPORTER_API_URL):
                if attempt < 2:
                    logging.info(f"Tor service is not up. Retry attempt {attempt + 1} of {n_retries + 1}.")
                    continue
                raise UserWarning(f"Tor service is not up at {TOR_HOST}:{SOCKS_PORT}.")
            else:
                logging.info("Tor service is up.")
                break
    except Exception as exception:
        log_string = f"While loading Chrome driver " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        del log_string

    # Check and set Chrome version environmental variable if missing
    if not os.environ.get("CHROME_VERSION"):
        chrome_version_main = get_chrome_version()
        logging.info(f"Environmental variable CHROME_VERSION is missing. Setting it to '{chrome_version_main}'.")
        os.environ["CHROME_VERSION"] = chrome_version_main
    CHROME_VERSION = os.environ.get("CHROME_VERSION")

    # Start chrome_driver
    try:
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument(f"--proxy-server={socks_socket}")
        chrome_driver = get_chrome_driver(
            options=chrome_options,
            chrome_driver_log_path=os.path.join(LOG_DIR_PATH, "chromedriver.log"))
    except Exception as exception:
        log_string = f"While loading Chrome driver " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        exit(1)

    # Get request url
    c24_request = get_c24_request(n_rooms=C24_N_ROOMS, areas=C24_AREAS)
    c24_request_url = c24_request.prepare().url

    # # Do the scraping
    # logging.info(f"Executing c24 scraping with url {c24_request_url}")
    # try:
    #     c24_page = uc_scrape_page(c24_request_url, chrome_driver)
    # except Exception as exception:
    #     log_string = f"While trying to scrape c24, " \
    #                  f"{type(exception).__name__} occurred: {exception}"
    #     logging.exception(log_string)
    #     del log_string
    #     c24_page = ""
    #
    # # Export results
    # if c24_page:
    #     if not os.path.exists(SCRAPED_PAGES_NEW_PATH):
    #         os.makedirs(SCRAPED_PAGES_NEW_PATH)
    #
    #     c24_export_file_name = f"{datetime.today().strftime('%Y_%m_%d_%H%M')}_{C24_INDICATOR}"
    #     with open(os.path.join(SCRAPED_PAGES_NEW_PATH, c24_export_file_name), "w", encoding="UTF-8") as c24_export_file:
    #         c24_export_file.write(c24_page)
    # else:
    #     log_string = "c24 scrape session unsuccessful!"
    #     logging.error(log_string)
    #     del log_string

    # Close tor service (shuts down tor container)
    try:
        if TOR_CONTROL_PORT is not None:
            tor_close_response = tor_operations.control_port_command(
                command="SIGNAL TERM",
                tor_host=TOR_HOST,
                tor_control_port=TOR_CONTROL_PORT,
                tor_control_port_password=TOR_CONTROL_PORT_PASSWORD)
            logging.info(f"Tor service shut down with response {tor_close_response}.")
        else:
            logging.info(f"Could not shut down tor service, "
                         f"because there is no TOR_CONTROL_PORT environmental variable.")
    except Exception as exception:
        log_string = f"While trying to close tor service, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        del log_string

    logging.info("c24 scraper finished")
