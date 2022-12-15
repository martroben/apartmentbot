
VOLUME_MOUNT_DIR: str = "/apartment_bot"
LOG_DIR: str = "/media/mart/Data/martroben/Projects/Python/apartment_bot/apartment_bot_py/log"
# f"{VOLUME_MOUNT_DIR}/log"
TOR_TORRC_PATH: str = "/etc/tor/torrc"
TOR_PROCESS_NAME: str = "tor"
TOR_CONTROL_PORT_PASSWORD: str               # Set by tor_operations.setup_tor() function
CHROME_VERSION: str = "108"
ACTIVE_LISTINGS_FILENAME: str = "active_listings.csv"
EXPIRED_LISTINGS_FILENAME: str = "expired_listings.csv"
MAX_REQUEST_ARCHIVE_SIZE_MB: float = 5
C24_INDICATOR: str = "c24"
KV_INDICATOR: str = "kv"
REQUESTS_ARCHIVE_DIR: str = "requests_archive"
# f"{VOLUME_MOUNT_DIR}/requests_archive"
KV_BASE_URL: str = "https://www2.kv.ee"
C24_BASE_URL: str = "https://m-api.city24.ee/et_EE/search/realties"
SQL_LISTING_TABLE_NAME: str = "listing"

# Gives error 451 (rejected for legal reasons) when using python requests module's default header.
USER_AGENT_HEADER: str = "curl/7.81.0"
