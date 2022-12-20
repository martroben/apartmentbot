# https://check.torproject.org/

import config

import re
import os
# import undetected_chromedriver as uc
from time import sleep
from urllib.error import ContentTooShortError
from stem.control import Controller
import logging
import socket


def socket_available(host: str, port: int):
    """
    Check if a socket accepts connections.

    :param host: Host (ip).
    :param port: Port.
    :return: True if connection can be established.
    """
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    available = socket_connection.connect_ex((host, port))                  # returns 0 if port is open
    socket_connection.close()
    return available == 0


def tor_control_getinfo(keyword: str = "info/names", password: str = "") -> str:
    """
    Sends a GETINFO request with input keyword to tor control port.
    Keywords: https://gitweb.torproject.org/torspec.git/tree/control-spec.txt - section 3.9 GETINFO.
    Alternative way to see all keywords: use request with "info/names" keyword.

    :param keyword: tor control port GETINFO keyword.
    :param password: tor control port password.
    :return: String with info returned by the tor control GETINFO command.
    """
    try:
        controller = Controller.from_port(port = config.TOR_CONTROL_PORT)
        controller.authenticate(password = password)
        response = controller.get_info(keyword)
        controller.close()
        return response
    except Exception as exception:
        log_string = f"While trying to GETINFO from tor control port with keyword '{keyword}', " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def check_tor_status():
    """
    Check if tor is up.
    First if tor control port accepts connections, second if tor GETINFO reports an active status.

    :return: True if tor is up, False otherwise.
    """
    try:
        if not socket_available("127.0.0.1", config.TOR_CONTROL_PORT):
            raise ConnectionError
    except ConnectionError as error:
        log_string = f"While checking tor status, {type(error).__name__} occurred: Couldn't reach the tor control port!"
        logging.error(log_string)
        return False

    tor_status = tor_control_getinfo(keyword="status/circuit-established", password= "")
    return tor_status == "1"


check_tor_status()





socks5_socket = f"socks5://127.0.0.1:{config.TOR_PORT}"
stem.Signal("HUP")

options = uc.ChromeOptions()
options.add_argument(f"--proxy-server={socks5_socket}")

try:
    driver = uc.Chrome(options=options, version_main=config.CHROME_VERSION)
except ContentTooShortError:
    print("content too short")

driver.get("https://www2.kv.ee/et/search?deal_type=1&county=1&parish=1061&rooms_min=2&rooms_max=2&city%5B0%5D=1011")
sleep(5)

# https://www.reddit.com/search/?q=r%2FCOVID19

response = driver.page_source
driver.quit()


# Test from saved kv data file
with open(f"{os.getcwd()}/sample_response.txt", "r") as sample_response:
    response = sample_response.read()


# https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/637
# https://devpress.csdn.net/python/62fe30f8c6770329308047f0.html
# https://stackoverflow.com/questions/30286293/make-requests-using-python-over-tor

