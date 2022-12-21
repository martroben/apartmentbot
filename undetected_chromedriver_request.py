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
import requests
import os
import signal
import psutil













socks5_socket = f"socks5://{config.LOCALHOST}:{config.TOR_PORT}"
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

