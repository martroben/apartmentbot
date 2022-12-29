from urllib.error import ContentTooShortError

import undetected_chromedriver
import undetected_chromedriver as uc
from time import sleep
import logging
import random
import os


def retry_function(times: int = 3, exceptions=Exception, retry_interval_sec: int = random.randint(3, 10)):
    """
    Retries the wrapped function. Meant to be used as a decorator.

    Optional parameters:
    times: int - The number of times to repeat the wrapped function (default: 3).
    exceptions: list[Exception] - List of exceptions that trigger a retry attempt (default: Exception).
    retry_interval_sec: int - How many seconds to wait between retry attempts (default: random integer between 3 and 10)
    """
    def decorator(function):
        def inner_function(*args, **kwargs):
            attempt = 1
            while attempt <= times:

                try:
                    return function(*args, **kwargs)
                except exceptions as exception:
                    log_string = f"Retrying function {function.__name__} in {retry_interval_sec} seconds, " \
                                 f"because {type(exception).__name__} exception occurred: {exception}\n" \
                                 f"Attempt {attempt} of {times}."
                    logging.exception(log_string)
                    sleep(retry_interval_sec)
                    attempt += 1
        return inner_function
    return decorator


@retry_function()
def uc_scrape_page(url: str, driver: undetected_chromedriver.Chrome):
    driver.get(url)
    sleep(5)
    scraped_data = driver.page_source
    return scraped_data


@retry_function(exceptions=ContentTooShortError)
def get_chrome_driver(options: undetected_chromedriver.ChromeOptions = uc.ChromeOptions(),
                      log_path: str = "/log/chromedriver.log"):

    if not os.path.isdir(os.path.dirname(log_path)):
        warning_string = f"Directory for logfile {chromedriver_log_path} doesn't exist. " \
                         f"This may cause Chrome driver to quit unexpectedly."
        raise UserWarning(warning_string)
    driver = uc.Chrome(options=options, service_log_path=log_path)
    driver.set_page_load_timeout(120)
    return driver


# Global
tor_host = "127.0.0.1"
socks_port = 9050
chrome_version = "108"
chromedriver_log_path = "/home/mart/apartment_bot/log/chromedriver.log"

# Input
scrape_urls = ["https://gitweb.torproject.org/torspec.git/tree/control-spec.txt",
               "https://www.reddit.com/search/?q=r%2FCOVID19"]

# Specify tor connection
# Socket format: https://devpress.csdn.net/python/62fe30f8c6770329308047f0.html
socks_socket = f"socks5://{tor_host}:{socks_port}"

chrome_options = uc.ChromeOptions()
chrome_options.add_argument(f"--proxy-server={socks_socket}")
# uc_options.add_argument("--headless")

try:
    chrome_driver = get_chrome_driver(chrome_options, chromedriver_log_path)
except Exception as exception:
    log_string = f"While loading Chrome driver " \
                 f"{type(exception).__name__} occurred: {exception}"
    logging.exception(log_string)
    exit(1)

scraped_pages = list()
for url in scrape_urls:
    try:
        scraped_pages += [uc_scrape_page(url=url, driver=chrome_driver)]
    except Exception as exception:
        log_string = f"While trying to load {url} in Chrome " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        scraped_pages += [f"{url}: NOTHING SCRAPED"]

chrome_driver.quit()
for page in scraped_pages:
    if len(page) < 300:
        print(page)
    else:
        print(len(page))
