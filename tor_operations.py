import config

import os
import re
import random
import string
import subprocess
import psutil
import logging


def setup_tor():
    """
    Sets up tor to be able to change ip-s in between requests.

    Uncomments the control port line in torrc file.
    Uncomments and sets a password hash for control port.
    Starts a tor process if it's not yet running.
    Needs to be run in admin rights to access torrc and start tor process

    :return: None
    """
    logging.info("Starting tor setup!")
    control_port_comment_pattern = re.compile(r"#\s*ControlPort\s*9051")
    control_port_password_comment_pattern = re.compile(r"^#\s*HashedControlPassword")
    control_port_password_pattern = re.compile(r"^HashedControlPassword.*$")

    # Generate control port password
    control_port_password = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    logging.info("Requesting tor to generate control port password hash...")
    control_port_password_hash = str()
    try:
        control_port_password_hash = subprocess.run(
            ["tor", "--quiet", "--hash-password", control_port_password],
            capture_output=True).stdout.strip().decode()
    except Exception as error:
        logging.error(f"{type(error)} {error}")
    if control_port_password_hash == "":
        logging.error("Couldn't generate control port password hash!")

    logging.info("Reading the current torrc file...")
    with open(config.TOR_TORRC_PATH, "r", encoding="utf-8") as torrc:
        original_torrc = torrc.readlines()

    # Rewrite torrc file to enable control port
    logging.info("Modifying torrc contents...")
    modified_torrc = list()
    try:
        for line in original_torrc:
            line = control_port_comment_pattern.sub("ControlPort 9051", line)
            line = control_port_password_comment_pattern.sub(f"HashedControlPassword", line)
            line = control_port_password_pattern.sub(f"HashedControlPassword {control_port_password_hash}", line)
            modified_torrc += [line]
    except Exception as error:
        logging.error(f"{type(error)} {error}")

    logging.info("Writing the modified torrc file...")
    try:
        with open(config.TOR_TORRC_PATH, "w", encoding="utf-8") as torrc:
            torrc.writelines(modified_torrc)
    except Exception as error:
        logging.error(f"{type(error)} {error}")

    # Write control port password on disk
    logging.info("Writing control port password on disk...")
    try:
        config.TOR_CONTROL_PORT_PASSWORD = control_port_password
        with open(f"{os.getcwd()}/control_port_password", "w") as password_file:
            password_file.write(control_port_password)
    except Exception as error:
        logging.error(f"{type(error)} {error}")

    # Start tor process
    logging.info("Checking if tor service is running...")
    tor_process = [process for process in psutil.process_iter() if process.name() == config.TOR_PROCESS_NAME]
    if tor_process:
        logging.info("tor service is already running!")
    else:
        logging.info("tor service was not running! Starting tor service...")
        subprocess.run(["service",  config.TOR_PROCESS_NAME, "start"])

    logging.info("tor setup complete!")

    return
