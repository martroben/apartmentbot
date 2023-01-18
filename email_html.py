
import os
import re
import csv
from datetime import datetime
import logging
import sqlite3
from dotenv import dotenv_values

import sys
sys.path.append("/home/mart/Python/apartmentbot/data_processor")
import sqlite_operations
from data_classes import Listing


def listing_to_html(listing: Listing) -> str:
    """
    Converts listing info to HTML list item that can be used in the e-mail HTML content.

    Listing items used:
    url: URL to listing web page.
    image_url: URL to listing image.
    address: Listing address.
    price: Listing price.
    n_rooms: Number of rooms.
    area_m2: Listing area in square meters.
    construction_year: Listing construction date.
    date_listed: Date listing was published.
    :return: String for HTML list item to be used in e-mail HTML.
    """

    # Format listing publishing date to a date string from epoch time
    date_listed_datetime = datetime.fromtimestamp(listing.date_listed)
    date_listed = date_listed_datetime.strftime("%Y-%m-%d%z")
    construction_year = "&nbsp;-&nbsp;" if listing.construction_year == 0 else listing.construction_year

    description_text = f"""\
        &emsp;Price: {int(listing.price_eur)} eur <br>\
        &emsp;Rooms: {listing.n_rooms} <br>\
        &emsp;Area: {listing.area_m2} m2 <br>\
        &emsp;Construction year: {construction_year} <br>\
        &emsp;Date listed: {date_listed}"""

    listing_html = """
        <li style="display: block; box-sizing: border-box; border-radius: 3px; text-align: left;\
        box-shadow: 1px 3px 1px 0 rgba(0, 0, 0, 0.08); border: 1px solid #cfcfcf; overflow: hidden;\
        background-color: #fff; font: normal 13px sans-serif; margin-bottom: 40px; max-width: 575px;">\
            <a href="{url}" style="float: left; width: 200px; height: 200px; display: block;\
            background-size: cover; background-image: url('{image_url}');">\
            </a>\
            <div style="float: left; box-sizing: border-box; max-width: 350px; padding: 20px;">\
                <h2 style="font-size: 16px; overflow: hidden; text-overflow: ellipsis;\
                white-space: nowrap; margin: 0;">\
                    <a href="{url}" style="color: #2b2b2b; text-decoration: none;">\
                        {address}\
                    </a>\
                </h2>\
                <p style="line-height: 20px; color: #5d5d5d; margin: 20px 0;">\
                    {description_text}\
                </p>\
            </div>\
        </li>""".format(
            url=listing.url,
            image_url=listing.image_url,
            address=listing.address,
            description_text=description_text)

    return re.sub(r" +", " ", listing_html)


def get_email_html(listings: list) -> str:
    """
    Turns listing information to a HTML string for e-mail

    :param listings: List of dicts containing listing information.
    :return: HTML string for e-mail HTML body
    """
    listing_htmls = [listing_to_html(**listing) for listing in listings]
    html_list_items_string = "\n<br>\n".join(listing_htmls)

    email_html = """
    <html>
        <head>
            <title>Apartment listings</title>
        </head>
        <body>
            <ul class="article-list-vertical" style="list-style: none;\
             margin: 0 auto; max-width: 600px; text-align: center; padding: 0;">
                {list_items}
            </ul>
        </body>
    </html>
    """.format(list_items=html_list_items_string)

    return email_html


###############
# Set logging #
###############

os.environ["LOG_DIR_PATH"] = "/home/mart/Python/apartmentbot/log"
LOG_DIR_PATH = os.environ["LOG_DIR_PATH"]
if not os.path.exists(LOG_DIR_PATH):
    os.makedirs(LOG_DIR_PATH)

logging.basicConfig(
    # stream=sys.stdout,
    filename=f"{LOG_DIR_PATH}/{datetime.today().strftime('%Y_%m')}.log",
    format="{asctime}|{funcName}|{levelname}:{message}",
    style="{",
    level=logging.INFO)

logging.info(f"\n\n\n{'-*-'*10} REPORTER STARTED {'-*-'*10}\n")


################################
# Load environmental variables #
################################

env_file_path = "/home/mart/Python/apartmentbot/.env"
env_variables = dotenv_values(env_file_path)

os.environ["C24_INDICATOR"] = env_variables["C24_INDICATOR"]
os.environ["SQL_DATABASE_PATH"] = "/home/mart/Python/apartmentbot/sql.db"
os.environ["SQL_LISTINGS_TABLE_NAME"] = env_variables["SQL_LISTINGS_TABLE_NAME"]
os.environ["SCRAPED_PAGES_NEW_PATH"] = "/home/mart/Python/apartmentbot/log/scraped_pages/new"
os.environ["SCRAPED_PAGES_PROCESSED_PATH"] = "/home/mart/Python/apartmentbot/log/scraped_pages/processed"

try:
    C24_INDICATOR = os.environ["C24_INDICATOR"]
    SQL_DATABASE_PATH = os.environ["SQL_DATABASE_PATH"]
    SQL_LISTINGS_TABLE_NAME = os.environ["SQL_LISTINGS_TABLE_NAME"]
    SCRAPED_PAGES_NEW_PATH = os.environ["SCRAPED_PAGES_NEW_PATH"]
    SCRAPED_PAGES_PROCESSED_PATH = os.environ["SCRAPED_PAGES_PROCESSED_PATH"]
except KeyError as error:
    log_string = f"While loading environmental variables " \
                 f"{type(error).__name__} occurred: {error}. Exiting!"
    logging.error(log_string)
    exit(1)


#########################
# Create sql connection #
#########################

logging.info(f"Establishing sql connection to {SQL_DATABASE_PATH}")
sql_connection = sqlite3.connect(SQL_DATABASE_PATH)
if not sqlite_operations.table_exists(SQL_LISTINGS_TABLE_NAME, sql_connection):
    logging.info(f"No sql table by the name {SQL_LISTINGS_TABLE_NAME}.")


###########
# Testing #
###########

sql_unreported_listings = sqlite_operations.read_data(
    table=SQL_LISTINGS_TABLE_NAME,
    connection=sql_connection,
    where="reported = 0 AND active = 1")

unreported_listings = [Listing().make_from_dict(sql_listing) for sql_listing in sql_unreported_listings]

print(listing_to_html(unreported_listings[0]))


##### CONTINUE HERE
print(get_email_html(unreported_listings))



reader = csv.DictReader("""\
id,portal,active,url,image_url,address,n_rooms,area_m2,price,date_added,date_scraped,date_removed,year_built
2028821,c24,1,https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kopli-tn/2960653,https://c24ee.img-bcg.eu/object/11/5191/2751785191.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kopli tn 64-5",3,62.4,307944.0,1662132928,1669651864.8203578,0.0,1999
2083903,c24,1,"https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kalaranna-21,/5576510",https://c24ee.img-bcg.eu/object/11/6377/1945436377.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kalaranna 21, 23-49",3,64.2,340000.0,1665144388,1669651864.8204205,0.0,2000
2083899,c24,1,"https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kalaranna-21,/1412295",https://c24ee.img-bcg.eu/object/11/6538/1614736538.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kalaranna 21, 23-18",3,63.7,340000.0,1665144379,1669651864.820465,0.0,2001
2058893,c24,1,https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kopli-tn/2361067,https://c24ee.img-bcg.eu/object/11/9640/3083689640.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kopli tn 54",3,79.4,199000.0,1665411491,1669651864.8205063,0.0,2002\
""".splitlines())

listings = [item for item in reader]

print(get_email_html(listings))

# use: https://htmlemail.io/inline/


# TO DO:
# Reverse html heading (street & apt first)

"""
<html>
    <head>
        <title>Apartment listings</title>
    </head>
    <body>
        <ul class="article-list-vertical" style="list-style: none;\
         margin: 0 auto; max-width: 600px; text-align: center; padding: 0;">
            <li style="display: block; box-sizing: border-box; border-radius: 3px; text-align: left; box-shadow: 1px 3px 1px 0 rgba(0, 0, 0, 0.08); border: 1px solid #cfcfcf; overflow: hidden; background-color: #fff; font: normal 13px sans-serif; margin-bottom: 40px; max-width: 575px;"> <a href="https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-mootori/8592646" style="float: left; width: 200px; height: 200px; display: block; background-size: cover; background-image: url('https://c24ee.img-bcg.eu/object/11/6925/1459866925.jpg');"> </a> <div style="float: left; box-sizing: border-box; max-width: 350px; padding: 20px;"> <h2 style="font-size: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin: 0;"> <a href="https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-mootori/8592646" style="color: #2b2b2b; text-decoration: none;"> &#129302 Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Mootori 7/2-8 </a> </h2> <p style="line-height: 20px; color: #5d5d5d; margin: 20px 0;"> &emsp;Price: 495000 eur <br> &emsp;Rooms: 3 <br> &emsp;Area: 85.7 m2 <br> &emsp;Construction year: &nbsp;-&nbsp; <br> &emsp;Date listed: 2022-12-19 </p> </div> </li>
            <li style="display: block; box-sizing: border-box; border-radius: 3px; text-align: left; box-shadow: 1px 3px 1px 0 rgba(0, 0, 0, 0.08); border: 1px solid #cfcfcf; overflow: hidden; background-color: #fff; font: normal 13px sans-serif; margin-bottom: 40px; max-width: 575px;"> <a href="https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-mootori/8592646" style="float: left; width: 200px; height: 200px; display: block; background-size: cover; background-image: url('https://c24ee.img-bcg.eu/object/11/6925/1459866925.jpg');"> </a> <div style="float: left; box-sizing: border-box; max-width: 350px; padding: 20px;"> <h2 style="font-size: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin: 0;"> <a href="https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-mootori/8592646" style="color: #2b2b2b; text-decoration: none;"> &#129302 Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Mootori 7/2-8 </a> </h2> <p style="line-height: 20px; color: #5d5d5d; margin: 20px 0;"> &emsp;Price: 495000 eur <br> &emsp;Rooms: 3 <br> &emsp;Area: 85.7 m2 <br> &emsp;Construction year: &nbsp;-&nbsp; <br> &emsp;Date listed: 2022-12-19 </p> </div> </li>
        </ul>
    </body>
</html>
"""
