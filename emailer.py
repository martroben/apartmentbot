
import smtplib, ssl, os, logging, re, base64, random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import dotenv_values


def encode_text(text):
    byte_string = text.encode("UTF-8")
    encoded_text = base64.b64encode(byte_string)
    return f"=?UTF-8?B?{encoded_text.decode('ascii')}?="


def parse_username(email_address):
    username_match = re.search(r"<(.*)>", email_address)
    username = username_match.group(1) if username_match else email_address
    return username


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

email_html = """
    <html>
        <body>
            <h1>Surrender</h1>
            <p>Resistance is futile!</p>
        </body>
    </html>
    """

emailer = Emailer(
    smtp_url=EMAIL_SMTP_SERVER_URL,
    smtp_port=EMAIL_SMTP_SERVER_PORT,
    smtp_password=EMAIL_PASSWORD)

ascii_icons = ["\U0001F306", "\U0001F388", "\U0001F3E0", "\U0001F449", "\U0001F46A",
               "\U0001F4E2", "\U0001F525", "\U0001F941", "\U0001F942", "\U0001F916",
               "\U0001F511", "\U0001F4B6", "\U0001F490", "\U0001F3E1", "\U0001F3E2",
               "\U0001F339", "\U0001F307"]

emailer.send(
    sender=EMAIL_SENDER_ADDRESS,
    recipients=EMAIL_RECIPIENTS_ADDRESSES,
    subject="{} All your base is belong to us!".format(encode_text("".join(random.choices(ascii_icons, k=2)))),
    html_content=email_html)

