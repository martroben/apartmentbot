# https://check.torproject.org/
import config

import re
import os
import undetected_chromedriver as uc
from time import sleep
from urllib.error import ContentTooShortError
from bs4 import BeautifulSoup
import data_processing

socks5_proxy = "socks5://127.0.0.1:9050"

options = uc.ChromeOptions()
options.add_argument(f"--proxy-server={socks5_proxy}")

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

kv_listings = []
scraper = BeautifulSoup(response, "html.parser")

# <span *class="large *stronger">.*(\d+)\s*$</span>

n_total_listings_pattern = re.compile(r'<span\s*class="large\s*stronger">.*?(\d+)\s*</span>')
n_total_listings_match = n_total_listings_pattern.search(response)
n_total_listings = int(n_total_listings_match.group(1)) if n_total_listings_match is not None else None



"""
<span class="large stronger"> <small> <a data-key="06a94ec6c58" href="/search&amp;deal_type=1&amp;county=1&amp;parish=1061&amp;city[0]=1001&amp;city[1]=1011&amp;rooms_min=3&amp;rooms_max=4&amp;rss=1" target="_blank" class="normal no-underline"> <i class="icon icon-feed"></i> </a> </small> Kuulutusi leitud 583 </span>"""


kv_listings_raw = scraper.find_all("article")
kv_listings += [data_processing.kv_get_listing_details(item) for item in kv_listings_raw]

for item in kv_listings:
    print(item)

# https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/637
# https://devpress.csdn.net/python/62fe30f8c6770329308047f0.html
# https://stackoverflow.com/questions/30286293/make-requests-using-python-over-tor

