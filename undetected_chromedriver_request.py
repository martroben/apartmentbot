# https://check.torproject.org/

import undetected_chromedriver as uc
from time import sleep
import logging


# Global
tor_host = "172.28.5.2"
socks_port = 9050
# chrome_version = "108"
log_path = "/log/chromedriver.log"

url = "https://check.torproject.org/"

# Specify tor connection
# Socket format: https://devpress.csdn.net/python/62fe30f8c6770329308047f0.html
socks_socket = f"socks5://{tor_host}:{socks_port}"
uc_options = uc.ChromeOptions()
uc_options.add_argument(f"--proxy-server={socks_socket}")
uc_options.add_argument("--headless")


try:
    chrome_driver = uc.Chrome(options=uc_options, service_log_path=log_path)
    chrome_driver.set_page_load_timeout(120)
    chrome_driver.get(url)
    sleep(10)
    scraped_page = chrome_driver.page_source
    chrome_driver.quit()
except Exception as exception:
    log_string = f"While trying to load {url} in Chrome " \
                 f"{type(exception).__name__} occurred: {exception}"
    logging.exception(log_string)
    scraped_page = ""

print(scraped_page)

# https://www.reddit.com/search/?q=r%2FCOVID19
# https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/637