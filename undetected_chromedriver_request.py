# https://check.torproject.org/

import config

import re
import os
# import undetected_chromedriver as uc
from time import sleep
from urllib.error import ContentTooShortError
import stem
from stem.control import Controller
import logging
import socket


def socket_available(host: str, port: int) -> bool:
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
        with Controller.from_port(port=config.TOR_CONTROL_PORT) as controller:
            controller.authenticate(password=password)
            response = controller.get_info(keyword)
            controller.close()
            return response
    except Exception as exception:
        log_string = f"While trying to GETINFO from tor control port with keyword '{keyword}', " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def check_tor_status() -> bool:
    """
    Check if tor is up.
    Checks first if tor control port accepts connections,
    second if tor GETINFO reports an active status.

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


import os
import signal
import psutil


def get_pids(process_name: str) -> list[int]:
    pids = [process.pid for process in psutil.process_iter(attrs=["name"])
            if process.name().lower() == process_name.lower()]
    return pids


def kill_tor_process() -> None:
    for pid in get_pids(config.TOR_PROCESS_NAME):
        os.kill(pid, signal.SIGTERM)
    return


def tor_signal_control_port(signal, password=""):
    try:
        with Controller.from_port(port=config.TOR_CONTROL_PORT) as controller:
            controller.authenticate(password=password)
            controller.signal(stem.Signal.HUP)
            return
    except Exception as exception:
        log_string = f"While trying to send a signal to tor control port, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def tor_signal_control_port():
    with Controller.from_port(port=config.TOR_CONTROL_PORT) as ctr:
        try:
            ctr.authenticate(password="")
            print(1)
        except Exception:
            print("problem1")
        try:
            ctr.signal(stem.Signal.HUP)
            print(2)
        except Exception:
            print("problem2")
        try:
            # gets stuck here
            ctr.close()
            print(3)
        except Exception:
            print("problem3")
        print(4)
        return "yes"


controller = Controller.from_port(port=config.TOR_CONTROL_PORT)
controller.authenticate(password="")
controller.signal(stem.Signal.HUP)
controller.close()

tor_signal_control_port()


os.kill(9208, signal.SIGHUP)




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

