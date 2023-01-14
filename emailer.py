import smtplib, ssl, os, logging, re
from email.message import EmailMessage
from dotenv import dotenv_values

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

try:
    EMAIL_SMTP_SERVER_URL = os.environ["EMAIL_SMTP_SERVER_URL"]
    EMAIL_SMTP_SERVER_PORT = int(os.environ["EMAIL_SMTP_SERVER_PORT"])
    EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
    EMAIL_SENDER_ADDRESS = os.environ["EMAIL_SENDER_ADDRESS"]
    EMAIL_RECIPIENTS_ADDRESSES = os.environ["EMAIL_RECIPIENTS_ADDRESSES"]
except KeyError as error:
    log_string = f"While loading environmental variables " \
                 f"{type(error).__name__} occurred: {error}. Exiting!"
    logging.error(log_string)
    exit(1)


###########
# Execute #
###########

msg = EmailMessage()
msg.set_content("Resistance is futile!")
msg['Subject'] = "All your base is belong to us!"
msg['From'] = EMAIL_SENDER_ADDRESS
msg['To'] = EMAIL_RECIPIENTS_ADDRESSES

email_username_match = re.search(r"<(.*)>", EMAIL_SENDER_ADDRESS)
email_username = email_username_match.group(1) if email_username_match else EMAIL_SENDER_ADDRESS
context = ssl.create_default_context()
with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER_URL, EMAIL_SMTP_SERVER_PORT, context=context) as server:
    server.login(email_username, EMAIL_PASSWORD)
    server.send_message(msg, from_addr=EMAIL_SENDER_ADDRESS, to_addrs=EMAIL_RECIPIENTS_ADDRESSES)
