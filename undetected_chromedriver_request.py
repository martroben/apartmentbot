from urllib.error import ContentTooShortError

import undetected_chromedriver as uc
from time import sleep
import logging
import random
import os

from selenium.common import TimeoutException
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webdriver import By
import selenium.webdriver.support.expected_conditions as EC  # noqa
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from undetected_chromedriver.webelement import UCWebElement

def get_wait_time():
    """
    Get a "human-like" wait time (for navigating to new page etc.)
    :return: Values between 5 and 20.
    """
    average_wait_time_sec = 3
    wait_time = random.expovariate(lambd=1/average_wait_time_sec)
    if wait_time < 3 or wait_time > 15:
        wait_time = get_wait_time()
    logging.info(f"Wait time: {round(wait_time,2)} seconds.")
    return wait_time


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


@retry_function(retry_interval_sec=get_wait_time())
def uc_scrape_page(url: str, driver: uc.Chrome):
    driver.get(url)
    sleep(5)
    scraped_data = driver.page_source
    return scraped_data


@retry_function(exceptions=ContentTooShortError)
def get_chrome_driver(options: uc.ChromeOptions = uc.ChromeOptions(),
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
navigate_url = "https://amiunique.org/fp"
scrape_urls = ["https://www.kv.ee/",
               # "https://gitweb.torproject.org/torspec.git/tree/control-spec.txt",
               # "https://www.reddit.com/search/?q=r%2FCOVID19"
               ]

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

chrome_driver.get(navigate_url)
type(chrome_driver.page_source)
sleep(30)

show_privacy_options_xpath = '//button[@id="onetrust-pc-btn-handler"]'
save_privacy_options_xpath = '//button[contains(@class, "save-preference-btn-handler")'
try:
    privacy_screen = WebDriverWait(chrome_driver, timeout=15).until(
        EC.presence_of_element_located((By.XPATH, show_privacy_options_xpath)))
    privacy_screen.find_element(By.XPATH, show_privacy_options_xpath).click()
    privacy_screen_extended = WebDriverWait(chrome_driver, timeout=15).until(
        EC.presence_of_element_located((By.XPATH, save_privacy_options_xpath)))
    privacy_screen_extended.find_element(By.XPATH, save_privacy_options_xpath).click()
except TimeoutException:
    log_string = f"Seems that no privacy screen was raised when loading {navigate_url}."
    logging.info(log_string)
sleep(get_wait_time())

county_dropdown_xpath = '//div[contains(@class, "short-search-county-parish")]//select[@id="county"]'
county_dropdown = chrome_driver.find_element(By.XPATH, county_dropdown_xpath)
Select(county_dropdown).select_by_visible_text("Tallinn")
sleep(get_wait_time())

area_name = "Põhja-Tallinn"
area_id_xpath = f'//label[text()[contains(., "{area_name}")]]'
area_id = chrome_driver.find_element(By.XPATH, area_id_xpath).get_attribute("for")

area_checkbox_xpath = f'//input[@type="checkbox"and @id="{area_id}"]'
area_checkbox = chrome_driver.find_element(By.XPATH, '//*[@for="city_1011"]')
area_checkbox.click()
sleep(get_wait_time())

rooms_min = 3
rooms_min_xpath = '//input[@id="rooms_min"]'
rooms_min_field = chrome_driver.find_element(By.XPATH, rooms_min_xpath)
rooms_min_field.send_keys(rooms_min)
sleep(get_wait_time())

rooms_max = 3
rooms_max_xpath = '//input[@id="rooms_max"]'
rooms_max_field = chrome_driver.find_element(By.XPATH, rooms_max_xpath)
rooms_max_field.send_keys(rooms_max)
sleep(get_wait_time())

search_buttons_xpath = '//button[contains(@class, "btn-search")]'
search_buttons = chrome_driver.find_elements(By.XPATH, search_buttons_xpath)
search_buttons[0].click()
sleep(20)


# xpath cleanup


# chrome.execute_script("arguments[0].click();", check_conditions)

# for item in county_dropdown.find_elements(By.XPATH, ".//*"):
#     print(item.text)



### FRAMES??

# county_dropdown._web_element_cls = uc.UCWebElement
# for item in county_dropdown.children():
#     print(item.text)

# Select(county_dropdown).select_by_value("1061")


# scraped_pages = list()
# for url in scrape_urls:
#     try:
#         scraped_pages += [uc_scrape_page(url=url, driver=chrome_driver)]
#     except Exception as exception:
#         log_string = f"While trying to load {url} in Chrome " \
#                      f"{type(exception).__name__} occurred: {exception}"
#         logging.exception(log_string)
#         scraped_pages += [f"{url}: NOTHING SCRAPED"]
#     sleep(get_wait_time())
#
#
# chrome_driver.quit()
#
# for page in scraped_pages:
#     if len(page) < 300:
#         print(page)
#     else:
#         print(len(page))

# TO DO:
# Create wrapper function for everything.
#
