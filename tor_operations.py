import config

import os
import re
import random
import string
import subprocess
import psutil
import logging
import socket
import stem
from stem.control import Controller
import signal
import requests
from time import sleep


def socket_available(host: str, port: int) -> bool:
    """
    Check if a socket accepts connections.

    :param host: Host (IP).
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


def tor_check_status() -> bool:
    """
    Check if tor is up.
    Checks first if tor control port accepts connections,
    second if tor GETINFO reports an active status.

    :return: True if tor is up, False otherwise.
    """
    try:
        if not socket_available(config.LOCALHOST, config.TOR_CONTROL_PORT):
            raise ConnectionError
    except ConnectionError as error:
        log_string = f"While checking tor status, {type(error).__name__} occurred: Couldn't reach the tor control port!"
        logging.error(log_string)
        return False

    tor_status = tor_control_getinfo(keyword="status/circuit-established", password=os.environ.get("TORRC_PASSWORD"))
    return tor_status == "1"


def get_pids(process_name: str) -> list[int]:
    """
    Gets pids of processes matching input process_name.

    :param process_name: Process name (exact match, case insensitive).
    :return: List of pids that match the process name.
    """
    pids = [process.pid for process in psutil.process_iter(attrs=["name"])
            if process.name().lower() == process_name.lower()]
    return pids


def kill_process(process_name: str, sighup: bool = False) -> None:
    """
    Kills process by name.

    :param process_name: Process name.
    :param sighup: Send SIGHUP signal instead of SIGTERM
    :return: None
    """
    for pid in get_pids(process_name):
        if sighup:
            os.kill(pid, signal.SIGHUP)
        else:
            os.kill(pid, signal.SIGTERM)
    return


def tor_signal_control_port(signal: stem.Signal, password: str = "") -> None:
    """
    Send a signal to tor control port.
    Additional info: https://gitweb.torproject.org/torspec.git/tree/control-spec.txt - section 3.7 SIGNAL.

    :param signal: Signal to send.
    :param password: Control port password.
    :return:
    """
    try:
        with Controller.from_port(port=config.TOR_CONTROL_PORT) as controller:
            controller.authenticate(password=password)
            controller.signal(signal)
            sleep(1)            # stem sometimes fails to close the connection -
        return                  # function gets stuck at exit without the sleep time.
    except Exception as exception:
        log_string = f"While trying to send a signal to tor control port, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def get_ip(tor: bool = False) -> str:
    """
    Check IP that is seen by an external service.

    :param tor: True = check tor IP. False = check regular IP.
    :return: Your IP, as the external API sees it.
    """
    socks5_proxies = {
        "http": f"socks5://{config.LOCALHOST}:{config.TOR_PORT}",
        "https": f"socks5://{config.LOCALHOST}:{config.TOR_PORT}"}
    try:
        if tor:
            response = requests.get(config.IP_REPORTER_API_URL, proxies=socks5_proxies)
        else:
            response = requests.get(config.IP_REPORTER_API_URL)
        return response.content.decode()

    except Exception as exception:
        log_string = f"While trying to check{' tor'*tor} ip, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def tor_reset_ip() -> bool:
    """
    Change tor ip. Tries to signal SIGHUP through tor control port first.
    If that fails, tries to send os kill SIGHUP signal to tor process
    From terminal: os.kill(<PID>, signal.SIGHUP)

    :return: None
    """
    old_tor_ip = get_ip(tor=True)
    try:
        tor_signal_control_port(stem.Signal.RELOAD)
    except Exception as exception:
        log_string = f"While trying to reset tor IP, " \
                     f"{type(exception).__name__} occurred: {exception}.\n" \
                     f"Trying to reset by os kill SIGHUP signal."
        logging.exception(log_string)
        
        kill_process(config.TOR_PROCESS_NAME, sighup=True)
        new_tor_ip = get_ip(tor=True)
        success = old_tor_ip != new_tor_ip
        if success:
            logging.info("Successfully reset tor IP by os kill SIGHUP signal.")
            return success
    
    new_tor_ip = get_ip(tor=True)
    success = old_tor_ip != new_tor_ip
    return success


def tor_setup_control_port(torrc_path: str, socks_port: (str, int) = 9050, control_port: (str, int) = 9051,
                           password: str = "", auto_generate_password:bool = False) -> None:
    """
    Sets up tor control port and control port password in torrc file.
    Saves password to environmental variables.

    :param torrc_path: torrc file path.
    :param port: Port number that is to be configured as the control port.
    :param password: What should be the control port password.
    :param auto_generate_password: Auto-generate password
    Uncomments the control port line in torrc file.
    Uncomments and sets a password hash for control port.

    :return: None
    """
    logging.info("Starting tor control port setup!")
    torrc_port_comment_pattern = re.compile(r"^#\s*ControlPort\s*9051")
    torrc_port_pattern = re.compile(r"^ControlPort.*$")
    torrc_password_comment_pattern = re.compile(r"^#\s*HashedControlPassword")
    torrc_password_pattern = re.compile(r"^HashedControlPassword.*$")

    # Auto-generate control port password
    if auto_generate_password:
        password = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    logging.info("Requesting tor to generate control port password hash...")
    password_hash = str()
    try:
        password_hash = subprocess.run(
            [config.TOR_PROCESS_NAME, "--quiet", "--hash-password", password],
            capture_output=True).stdout.strip().decode()
    except Exception as exception:
        log_string = f"While trying to generate tor control port password hash, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
    if password_hash == "":
        logging.error("Failed to generate control port password hash!")

    logging.info("Reading the current torrc file...")
    with open(torrc_path, "r", encoding="utf-8") as torrc:
        original_torrc = torrc.readlines()

    # Rewrite torrc file to enable control port
    logging.info("Modifying torrc contents...")
    modified_torrc = list()
    try:
        for line in original_torrc:
            if str(port) != 9051:
                line = torrc_port_comment_pattern.sub("ControlPort 9051", line)
                line = torrc_port_pattern.sub(f"ControlPort {port}", line)
            if auto_generate_password or password != "":
                line = torrc_password_comment_pattern.sub(f"HashedControlPassword", line)
                line = torrc_password_pattern.sub(f"HashedControlPassword {password_hash}", line)
            modified_torrc += [line]
    except Exception as exception:
        log_string = f"While trying to read existing torrc file, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)

    logging.info("Writing the modified torrc file...")
    try:
        with open(torrc_path, "w", encoding="utf-8") as torrc:
            torrc.writelines(modified_torrc)
    except Exception as exception:
        log_string = f"While trying to write the modified torrc file, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)

    # Save control port password to environmental variables
    logging.info("Writing control port password to environmental variables...")
    try:
        os.environ["TOR_CONTROL_PORT_PASSWORD"]
    except Exception as exception:
        log_string = f"While trying to save tor control port password to environmental variables, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)

    logging.info("tor control port setup complete!")
    return


tor_setup_control_port(config.TOR_TORRC_PATH)



    # Enforce new settings
    logging.info("Checking if tor service is running...")
    tor_processes = [process for process in psutil.process_iter() if process.name() == config.TOR_PROCESS_NAME]
    if tor_processes:
        logging.info("tor service is already running. Resetting...")

    else:
        logging.info("tor service was not running! Starting tor service.")
        subprocess.run(["service",  config.TOR_PROCESS_NAME, "start"])


