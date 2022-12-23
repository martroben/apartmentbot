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
    # Dependencies: get_pids
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
    If that fails, tries to send os kill SIGHUP signal to tor process.
    From terminal: os.kill(<PID>, signal.SIGHUP)

    :return: None
    """
    # Dependencies: get_ip, tor_signal_control_port, kill_process

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


def torrc_modify_line(pattern: re.Pattern, replace:str, torrc_contents: list[str]) -> None:
    """
    Set or replace value in a line of torrc (tor config file).

    :param pattern: Regex pattern object that matches torrc line to be replaced.
    :param replace: Replacement string.
    :param torrc_contents: List of torrc lines.
    :return: None
    """

    n_matches = 0
    modified_torrc = list()
    for line in torrc_contents:
        line = pattern.sub(replace, line)
        modified_torrc += [line]
        n_matches += bool(pattern.search(line))

    if n_matches == 0:
        modified_torrc += [replace]
        log_string = f"No matches found in torrc file when setting '{replace}'! " \
                     f"Added line '{replace}' to torrc."
        logging.warning(log_string)
    if n_matches > 1:
        log_string = f"{n_matches} matching lines found in torrc file when setting '{replace}'! " \
                     f"(Expected to get a single match.) " \
                     f"Modified all of the matching lines."
        logging.warning(log_string)

    return


def tor_get_password_hash(password: str) -> str:
    """
    Request password hash from tor process.

    :param password: Password that is to be hashed.
    :return: tor-specific hash string of the input password.
    """
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

    return password_hash


def torrc_set_values(torrc_lines: list[str], socks_port: (int, str) = "", control_port: (int, str) = "",
                control_port_password: str = "", auto_generate_password: bool = False) -> None:
    """
    Set values of input parameters in torrc (tor config) file.
    Default values don't modify the torrc file.
    Saves control port password to environmental variables, if password is to be set.

    :param torrc_lines: List of torrc lines.
    :param socks_port: Socks5 port on localhost.
    :param control_port: Tor control port.
    :param control_port_password: Control port password.
    :param auto_generate_password: Auto generate control port password.
    :return: None
    """
    if socks_port:
        socks_port_parameter = "SocksPort"
        logging.info(f"Setting torrc {socks_port_parameter} value to {socks_port}")
        # Match "# SocksPort 9050" and "SocksPort 10", but not "# SocksPort 192.168.0.1"
        socks_port_pattern = re.compile(rf"^#*\s*{socks_port_parameter}(?!\s*\d{{1,3}}\.\d{{1,3}}).*$")
        socks_port_replacement = f"{socks_port_parameter} {socks_port}"
        torrc_modify_line(socks_port_pattern, socks_port_replacement, torrc_lines)

    if control_port:
        control_port_parameter = "ControlPort"
        logging.info(f"Setting torrc {control_port_parameter} value to {control_port}")
        control_port_pattern = re.compile(rf"^#*\s*{control_port_parameter}.*$")
        control_port_replacement = f"{control_port_parameter} {control_port}"
        torrc_modify_line(control_port_pattern, control_port_replacement, torrc_lines)

    if control_port_password or auto_generate_password:
        control_port_password_parameter = "HashedControlPassword"
        logging.info(f"Setting torrc {control_port_password_parameter} value{auto_generate_password*' automatically'}.")
        # Auto-generate random password and save it as environmental variable
        if auto_generate_password:
            os.environ["TOR_CONTROL_PORT_PASSWORD"] = "".join(random.choices(
                population=string.ascii_uppercase + string.digits,
                k=8))
        else:
            os.environ["TOR_CONTROL_PORT_PASSWORD"] = control_port_password
        control_port_password_value = tor_get_password_hash(os.environ.get("TOR_CONTROL_PORT_PASSWORD"))
        control_port_password_pattern = re.compile(rf"^#*\s*{control_port_password_parameter}.*$")
        control_port_password_replacement = f"{control_port_password_parameter} {control_port_password_value}"
        torrc_modify_line(control_port_password_pattern, control_port_password_replacement, torrc_lines)

    return


try:
    with open(config.TORRC_PATH, "r", encoding="utf-8") as torrc:
        torrc_lines = torrc.readlines()
except Exception as exception:
    log_string = f"While trying to open torrc file, " \
                 f"{type(exception).__name__} occurred: {exception}"
    logging.exception(log_string)

try:
    torrc_set_values(torrc_lines)
except Exception as exception:
    log_string = f"While trying to modify torrc lines, " \
                 f"{type(exception).__name__} occurred: {exception}"
    logging.exception(log_string)

try:
    with open(config.TORRC_PATH, "w", encoding="utf-8") as torrc:
        torrc.writelines(config.TORRC_PATH)
except Exception as exception:
    log_string = f"While trying to write the modified torrc file, " \
                 f"{type(exception).__name__} occurred: {exception}"
    logging.exception(log_string)

try:
    tor_processes = [process for process in psutil.process_iter() if process.name() == config.TOR_PROCESS_NAME]
    if tor_processes:
        logging.info("tor services already running. Resetting...")
        for process in tor_processes:
            kill_process(process.name())

    logging.info("Starting new tor service")
    subprocess.run(["service",  config.TOR_PROCESS_NAME, "start"])
except Exception as exception:
    log_string = f"While trying to start tor service with new configuration, " \
                 f"{type(exception).__name__} occurred: {exception}"
    logging.exception(log_string)
