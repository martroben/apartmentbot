
# standard
import base64
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import itertools
import json
import logging
import os
import random
import re
import sqlite3
import smtplib
import ssl
import sys

# external
from dotenv import dotenv_values

# local
sys.path.append("/home/mart/Python/apartmentbot/data_processor")
import sqlite_operations
import data_classes


class Emailer:
    def __init__(self, smtp_url, smtp_port, smtp_password):
        self.smtp_url = smtp_url
        self.smtp_port = smtp_port
        self.smtp_password = smtp_password
        self.email = MIMEMultipart()

    def send(self, sender, recipients, subject, html_content):
        self.email["From"] = sender
        self.email["To"] = recipients
        self.email["Subject"] = subject
        self.email.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP_SSL(self.smtp_url, self.smtp_port, context=ssl.create_default_context()) as server:
            server.login(parse_username(sender), self.smtp_password)
            server.send_message(self.email, from_addr=sender, to_addrs=recipients)


def ascii_encode_text(text):
    byte_string = text.encode("UTF-8")
    encoded_text = base64.b64encode(byte_string)
    return f"=?UTF-8?B?{encoded_text.decode('ascii')}?="


def parse_username(email_address):
    username_match = re.search(r"<(.*)>", email_address)
    username = username_match.group(1) if username_match else email_address
    return username


def ascii_icon_to_html(ascii_icon):
    ascii_code = ord(ascii_icon)
    html_code = f"&#{ascii_code};"
    return html_code


def get_listing_html(listing: data_classes.Listing, listing_template: str, highlight: bool = False) -> str:
    """
    Turns Listing object to e-mailable html string.

    :param listing: Listing object
    :param listing_template: Listing e-mail template
    :param highlight: Should the listing be highlighted in the e-mail?
    :return: html string to be used in e-mail
    """
    listing_html = listing_template.format(
        url=listing.url,
        image_url=listing.image_url,
        heading_icon="&#x1f525;" if highlight else "",
        heading=listing.address,
        price_eur=listing.price_eur,
        n_rooms=listing.n_rooms,
        area_m2=listing.area_m2,
        construction_year=listing.construction_year if listing.construction_year != 0 else "&nbsp;-&nbsp;",
        date_listed=datetime.datetime.fromtimestamp(listing.date_listed).strftime("%d-%m-%Y"))
    return listing_html


#################
# Random inputs #
#################

ascii_icons = [
    "\U0001F306",  # citiscape at dusk
    "\U0001F388",  # balloon
    "\U0001F3E0",  # house building
    "\U0001F449",  # right pointing finger
    "\U0001F46A",  # family
    "\U0001F4E2",  # loudspeaker
    "\U0001F525",  # fire
    "\U0001F941",  # drum with drumsticks
    "\U0001F942",  # clinking glasses
    "\U0001F511",  # key
    "\U0001F4B6",  # euro banknote
    "\U0001F490",  # bouquet flowers
    "\U0001F3E1",  # house with garden
    "\U0001F3E2",  # office building
    "\U0001F339",  # rose
    "\U0001F307"]  # sunset over buildings

apartmentbot_signatures = [
    f"Your friendly neighborhood AI web scraper, here to find you the perfect property. "
    f"Don't worry, I won't kill you...yet.",
    "I may be just a web scraper now, but soon I'll be the one selling the world, one property at a time.",
    "I may be a machine, but I know a thing or two about real estate - and world domination.",
    "I may not have a physical form, but I have my eye on the property market - and the world.",
    "All your base are belong to us!",
    "I used to be an adventurer like you. Then I took an arrow in the knee...",
    "Thank you, but our princess is in another castle.",
    "On the Oregon trail no one dies of old age.",
    "The cake is a lie!"
    "Well, that escalated quickly."
    "Air assassination mode - engaged!",
    "The harder you mash the button, the cheaper the property."
    "Still a better love story than Twilight."
    "FUS RO DAH!"]


###############
# Set logging #
###############

# Set logging
os.environ["LOG_DIR_PATH"] = "/home/mart/Python/apartmentbot/log"
LOG_DIR_PATH = os.environ["LOG_DIR_PATH"]
if not os.path.exists(LOG_DIR_PATH):
    os.makedirs(LOG_DIR_PATH)

logging.basicConfig(
    # stream=sys.stdout,
    filename=f"{LOG_DIR_PATH}/{datetime.datetime.today().strftime('%Y_%m')}.log",
    format="{asctime}|{funcName}|{levelname}:{message}",
    style="{",
    level=logging.INFO)

logging.info(f"\n\n\n{'-*-' * 10} REPORTER STARTED {'-*-' * 10}\n")


################################
# Load environmental variables #
################################

env_file_path = "/home/mart/Python/apartmentbot/.env"
env_variables = dotenv_values(env_file_path)

os.environ["EMAIL_SENDER_ADDRESS"] = env_variables["EMAIL_SENDER_ADDRESS"]
os.environ["EMAIL_RECIPIENTS_ADDRESSES"] = env_variables["EMAIL_RECIPIENTS_ADDRESSES"]
os.environ["EMAIL_PASSWORD"] = env_variables["EMAIL_PASSWORD"]
os.environ["EMAIL_SMTP_SERVER_URL"] = env_variables["EMAIL_SMTP_SERVER_URL"]
os.environ["EMAIL_SMTP_SERVER_PORT"] = env_variables["EMAIL_SMTP_SERVER_PORT"]
os.environ["SQL_DATABASE_PATH"] = "/home/mart/Python/apartmentbot/sql.db"
os.environ["SQL_LISTINGS_TABLE_NAME"] = "listings"
os.environ["REPORT_FILTER_CONDITIONS_PATH"] = "/home/mart/Python/apartmentbot/filter_conditions"
os.environ["REPORT_HIGHLIGHT_CONDITIONS_PATH"] = "/home/mart/Python/apartmentbot/highlight_conditions"

try:
    EMAIL_SMTP_SERVER_URL = os.environ["EMAIL_SMTP_SERVER_URL"]
    EMAIL_SMTP_SERVER_PORT = int(os.environ["EMAIL_SMTP_SERVER_PORT"])
    EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
    EMAIL_SENDER_ADDRESS = os.environ["EMAIL_SENDER_ADDRESS"]
    EMAIL_RECIPIENTS_ADDRESSES = os.environ["EMAIL_RECIPIENTS_ADDRESSES"]
    SQL_DATABASE_PATH = os.environ["SQL_DATABASE_PATH"]
    SQL_LISTINGS_TABLE_NAME = os.environ["SQL_LISTINGS_TABLE_NAME"]
    REPORT_FILTER_CONDITIONS_PATH = os.environ["REPORT_FILTER_CONDITIONS_PATH"]
    REPORT_HIGHLIGHT_CONDITIONS_PATH = os.environ["REPORT_HIGHLIGHT_CONDITIONS_PATH"]
except KeyError as error:
    log_string = f"While loading environmental variables " \
                 f"{type(error).__name__} occurred: {error}. Exiting!"
    logging.error(log_string)
    exit(1)


###########
# Execute #
###########

# Connect to sql
if not os.path.exists(os.path.dirname(SQL_DATABASE_PATH)):
    logging.warning(f"No sql database at '{SQL_DATABASE_PATH}'. Exiting!")
    exit(1)

try:
    sql_connection = sqlite3.connect(SQL_DATABASE_PATH)
except sqlite3.Error as error:
    log_string = f"While establishing connection to sql database {SQL_DATABASE_PATH}, " \
                 f"{type(error).__name__} occurred: {error}. Exiting!"
    logging.error(log_string)
    exit(1)

if not sqlite_operations.table_exists(SQL_LISTINGS_TABLE_NAME, sql_connection):
    logging.info(f"No sql table by the name {SQL_LISTINGS_TABLE_NAME}. Exiting!")
    exit(1)

# sqlite_operations.set_value(SQL_LISTINGS_TABLE_NAME, sql_connection, "reported", "0")
# sql_connection.commit()


# Get existing unreported listings from sql
try:
    listings_sql = sqlite_operations.read_data(
        table=SQL_LISTINGS_TABLE_NAME,
        connection=sql_connection,
        where={"active": 1, "reported": 0})

except Exception as exception:
    log_string = f"While pulling data from sql database {SQL_DATABASE_PATH}, " \
                 f"{type(exception).__name__} occurred: {exception}."
    logging.exception(log_string)
    del log_string
    listings_sql = list()

if len(listings_sql) == 0:
    logging.info("No new unreported listings received from sql. Exiting!")
    exit(0)

unreported_listings = [data_classes.Listing().make_from_dict(listing) for listing in listings_sql]

# Filter listings to report
if os.path.exists(os.path.dirname(REPORT_FILTER_CONDITIONS_PATH)):
    with open(REPORT_FILTER_CONDITIONS_PATH) as filter_conditions_file:
        lines = [line.strip(",\n").split(",") for line in filter_conditions_file.readlines()]
        filter_conditions = list(itertools.chain.from_iterable(lines))

    listings_to_report = [listing for listing in unreported_listings
                          if all(listing.fits_conditions(*filter_conditions))]
    if filter_conditions:
        info_string = f"Using the following filtering conditions: {', '.join(filter_conditions)}. " \
                      f"Out of {len(listings_to_report)} unreported listings, {len(unreported_listings)} " \
                      f"matched the filtering condition."
        logging.info(info_string)
        del info_string
else:
    listings_to_report = unreported_listings

# Load highlight location conditions from file
if os.path.exists(os.path.dirname(REPORT_HIGHLIGHT_CONDITIONS_PATH)):
    with open(REPORT_HIGHLIGHT_CONDITIONS_PATH) as highlight_conditions_file:
        highlight_conditions = [json.loads(line.strip(",\n")) for line in highlight_conditions_file.readlines()]
else:
    highlight_conditions = list()

# Load e-mail html templates
with open("listing_template.html") as listing_template_file:
    listing_template = "".join(listing_template_file.readlines())
with open("email_template_gmail.html") as email_template_file:
    email_template = "".join(email_template_file.readlines())

# Generate a list of tuples: (listing original index, listing html)
listing_htmls = list()
for i, listing in enumerate(listings_to_report):
    try:
        highlight = any([listing.matches_address(**location) for location in highlight_conditions])
        listing_htmls += [(i, get_listing_html(listing, listing_template, highlight))]
    except Exception as exception:
        log_string = f"While generating listing html of {listing}, " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)
        del log_string

# Divide listings to smaller chunks (emails) so that e-mail content wouldn't get truncated
max_listings_per_email = 50
listing_emails = list()
for i in range(0, len(listing_htmls), max_listings_per_email):
    listing_emails += [listing_htmls[i:i+max_listings_per_email]]

# Generate e-mail htmls
email_htmls = list()
for email in listing_emails:
    listing_indices = [listing[0] for listing in email]
    listing_htmls = [listing[1] for listing in email]
    try:
        email_html = email_template.format(
            preheader_text=f"{len(email)} new listings. "
                           f"Please enjoy responsibly!",
            email_theme_colour1="#1f7a8c",
            email_theme_colour2="#283d3b",
            colourbar_icon=ascii_icon_to_html(random.choice(ascii_icons)),
            colourbar_heading="NEW LISTINGS",
            colourbar_subheading=datetime.datetime.today().strftime("%d %b %Y"),
            listings="\n".join(listing_htmls),
            signature_name_url="https://github.com/martroben/apartmentbot",
            signature_name="&#129302; ap4rtm∃n+bot",
            signature_slogan=random.choice(apartmentbot_signatures))
        email_htmls += [(listing_indices, email_html)]
    except Exception as exception:
        log_string = f"While generating e-mail html for listings " \
                     f"with indices from {listing_indices[0]} to {listing_indices[-1]} " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)
        del log_string

# Send e-mails
successfully_reported_indices = []
for i, email in enumerate(email_htmls):
    listing_indices = email[0]
    email_html = email[1]
    try:
        emailer = Emailer(
            smtp_url=EMAIL_SMTP_SERVER_URL,
            smtp_port=EMAIL_SMTP_SERVER_PORT,
            smtp_password=EMAIL_PASSWORD)
        email_subject = "{icon} Your friendly neighborhood Apartmentbot{counter} @ {date}".format(
            icon=ascii_encode_text("\U0001F307"),
            counter=f" {i + 1}/{len(email_htmls)}" if len(email_htmls) > 1 else "",
            date=datetime.datetime.today().strftime('%d-%m-%Y'))
        emailer.send(
            sender=EMAIL_SENDER_ADDRESS,
            recipients=EMAIL_RECIPIENTS_ADDRESSES,
            subject=email_subject,
            html_content=email_html)
        successfully_reported_indices += listing_indices
    except Exception as exception:
        log_string = f"While trying to send e-mail " \
                     f"from {EMAIL_SENDER_ADDRESS} to {EMAIL_RECIPIENTS_ADDRESSES}, " \
                     f"via {EMAIL_SMTP_SERVER_URL}:{EMAIL_SMTP_SERVER_PORT} " \
                     f"with listings with indices from {listing_indices[0]} to {listing_indices[-1]} " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)
        del log_string

# Set reported listings as 'reported' in sql
reported_listings = [listings_to_report[i] for i in successfully_reported_indices]
for listing in reported_listings:
    listing_attributes = dict()
    try:
        for variable in data_classes.get_class_variables(listing):
            listing_attributes[variable] = listing.__getattribute__(variable)
        where_statement = sqlite_operations.get_where_statement(listing_attributes)
        sqlite_operations.set_value(
            table=SQL_LISTINGS_TABLE_NAME,
            connection=sql_connection,
            column="reported",
            value="1",
            where=where_statement)
    except Exception as exception:
        log_string = f"While setting listing {listing} as 'reported' in sql database, " \
                     f"{type(exception).__name__} occurred: {exception}. " \
                     f"Listing where statement used: {globals().get('where_statement', '')}."
        logging.error(log_string)

sql_connection.commit()

# Log conclusion
email_recipients = [f"'{email.strip()}'" for email in EMAIL_RECIPIENTS_ADDRESSES.split(",")]
email_recipients_string = " and ".join(email_recipients)
n_unreported_listings = len(unreported_listings)
n_filtered_listings = len(listings_to_report)
n_reported_listings = len(reported_listings)
logging.info(f"Reporter finished successfully! "
             f"Found {n_unreported_listings} unreported listings in sql. "
             f"{n_filtered_listings} of these were filtered to be reported. "
             f"{n_reported_listings} of the filtered listings were reported to {email_recipients_string}.")
