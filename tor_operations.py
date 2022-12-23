
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
import argparse
from time import sleep
from datetime import date


def socket_available(host: str, port: (int, str)) -> bool:
    """
    Check if a socket accepts connections.

    :param host: Host (IP).
    :param port: Port.
    :return: True if connection can be established.
    """
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    available = socket_connection.connect_ex((host, int(port)))                  # returns 0 if port is open
    socket_connection.close()
    return available == 0


def tor_control_getinfo(tor_control_port: (int, str), keyword: str = "info/names", password: str = "") -> str:
    """
    Sends a GETINFO request with input keyword to tor control port.
    Keywords: https://gitweb.torproject.org/torspec.git/tree/control-spec.txt - section 3.9 GETINFO.
    Alternative way to see all keywords: use request with "info/names" keyword.

    :param tor_control_port: Port number of the tor control port.
    :param keyword: tor control port GETINFO keyword.
    :param password: tor control port password.
    :return: String with info returned by the tor control GETINFO command.
    """
    try:
        with Controller.from_port(port=int(tor_control_port)) as controller:
            controller.authenticate(password=password)
            response = controller.get_info(keyword)
            controller.close()
            return response
    except Exception as exception:
        log_string = f"While trying to GETINFO from tor control port with keyword '{keyword}', " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def tor_check_status(tor_control_port: (int, str), tor_control_port_password: str, localhost_ip: str) -> bool:
    """
    Check if tor is up.
    Checks first if tor control port accepts connections,
    second if tor GETINFO reports an active status.

    :param tor_control_port: Port number of the tor control port.
    :param tor_control_port_password: Password to allow controlling tor via the control port.
    :param localhost_ip: IP of localhost.
    :return: True if tor is up, False otherwise.
    """
    try:
        if not socket_available(localhost_ip, tor_control_port):
            raise ConnectionError
    except ConnectionError as error:
        log_string = f"While checking tor status, {type(error).__name__} occurred: Couldn't reach the tor control port!"
        logging.error(log_string)
        return False

    tor_status = tor_control_getinfo(
        tor_control_port=tor_control_port,
        keyword="status/circuit-established",
        password=tor_control_port_password)
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


def tor_signal_control_port(tor_control_port: (int, str), signal_code: stem.Signal, password: str = "") -> None:
    """
    Send a signal to tor control port.
    Additional info: https://gitweb.torproject.org/torspec.git/tree/control-spec.txt - section 3.7 SIGNAL.

    :param tor_control_port: Port number of the tor control port.
    :param signal_code: Signal to send (e.g. TERM, HUP etc.).
    :param password: Control port password.
    :return:
    """
    try:
        with Controller.from_port(port=tor_control_port) as controller:
            controller.authenticate(password=password)
            controller.signal(signal_code)
            sleep(1)            # stem sometimes fails to close the connection -
        return                       # function gets stuck at exit without the sleep time.
    except Exception as exception:
        log_string = f"While trying to send a signal to tor control port, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def get_ip(ip_api_url: str, localhost_ip: str = "127.0.0.1", socks_port: (int, str) = 9050, tor: bool = False) -> str:
    """
    Check IP that is seen by an external service.

    :param ip_api_url: URL of some API service that returns caller IP.
    :param localhost_ip: IP of localhost.
    :param socks_port: Port number of socks5 port.
    :param tor: True = check tor IP. False = check regular IP.
    :return: Your IP, as the external API sees it.
    """
    socks5_proxies = {
        "http": f"socks5://{localhost_ip}:{socks_port}",
        "https": f"socks5://{localhost_ip}:{socks_port}"}
    try:
        if tor:
            response = requests.get(ip_api_url, proxies=socks5_proxies)
        else:
            response = requests.get(ip_api_url)
        ip = response.content.decode()
        if not re.match(r"\d{1,3}\.\d{1,3}.\d{1,3}.\d{1,3}", ip):
            raise UserWarning(f"'{ip}' is not in the standard format of IPv4.")
        return ip

    except Exception as exception:
        log_string = f"While trying to check{' tor'*tor} ip, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def tor_reset_ip(tor_control_port: (int, str) = 9051, tor_control_port_password: str = "",
                 verify_ip_change: bool = False, socks_port: (int, str) = 9050, tor_process_name: str = "tor",
                 localhost_ip: str = "127.0.0.1", ip_api_url: str = "") -> bool:
    """
    Change tor ip.

    If verify_ip_change = False:
    signals SIGHUP to tor control port.
    Equivalent of terminal os.kill(<PID>, signal.SIGHUP)

    If verify_ip_change = True:
    Tries to signal SIGHUP through tor control port first.
    If that fails, tries to send os kill SIGHUP signal to tor process.
    Verifies that tor ip after reset is different from the initial one.

    :param tor_control_port: Port number of the tor control port.
    :param tor_control_port_password: Password set to tor control port to allow changes via the control port.
    :param verify_ip_change: Verify that tor ip after reset is different from the initial one.
    :param socks_port: Port number of the socks5 port.
    :param tor_process_name: Name of tor process to call.
    :param localhost_ip: IP of localhost.
    :param ip_api_url: URL of some API service that returns caller IP.
    :return: True if IP changed successfully, False if initial IP is the same as changed IP.
    """
    # Dependencies: get_ip, tor_signal_control_port, kill_process
    if not verify_ip_change:
        tor_signal_control_port(int(tor_control_port), stem.Signal.RELOAD, tor_control_port_password)
        return True
    else:
        old_tor_ip = get_ip(ip_api_url, localhost_ip, socks_port, tor=True)
        try:
            tor_signal_control_port(int(tor_control_port), stem.Signal.RELOAD, tor_control_port_password)
        except Exception as exception:
            log_string = f"While trying to reset tor IP, " \
                         f"{type(exception).__name__} occurred: {exception}.\n" \
                         f"Trying to reset by os kill SIGHUP signal."
            logging.exception(log_string)

            kill_process(tor_process_name, sighup=True)
            new_tor_ip = get_ip(ip_api_url, localhost_ip, socks_port, tor=True)
            success = old_tor_ip != new_tor_ip
            if success:
                logging.info("Successfully reset tor IP by os kill SIGHUP signal.")
                return success

        new_tor_ip = get_ip(ip_api_url, localhost_ip, socks_port, tor=True)
        success = old_tor_ip != new_tor_ip
        return success


def torrc_modify_line(pattern: re.Pattern, replace: str, torrc_contents: list[str]) -> None:
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


def tor_get_password_hash(password: str, tor_process_name: str) -> str:
    """
    Request password hash from tor process.

    :param password: Password that is to be hashed.
    :param tor_process_name: Name of tor process to call.
    :return: tor-specific hash string of the input password.
    """
    logging.info("Requesting tor to generate control port password hash...")
    password_hash = str()
    try:
        password_hash = subprocess.run(
            [tor_process_name, "--quiet", "--hash-password", password],
            capture_output=True).stdout.strip().decode()
    except Exception as exception:
        log_string = f"While trying to generate tor control port password hash, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
    if password_hash == "":
        logging.error("Failed to generate control port password hash!")

    return password_hash


def torrc_set_values(torrc_lines: list[str], socks_port: (int, str) = "", tor_control_port: (int, str) = "",
                     tor_process_name: str = "tor", tor_control_port_password: str = "",
                     auto_generate_password: bool = False) -> None:
    """
    Set values of input parameters in torrc (tor config) file.
    Default values don't modify the torrc file.
    Saves control port password to environmental variables, if password is to be set.

    :param torrc_lines: List of torrc lines.
    :param socks_port: Socks5 port on localhost.
    :param tor_control_port: Tor control port.
    :param tor_process_name: Name of tor process.
    :param tor_control_port_password: Password to set to controlling tor via control port.
    :param auto_generate_password: Auto generate control port password.
    :return: None
    """
    socks_port_parameter = "SocksPort"
    control_port_parameter = "ControlPort"
    control_port_password_parameter = "HashedControlPassword"

    if socks_port:
        logging.info(f"Setting torrc {socks_port_parameter} value to {socks_port}")
        # Match "# SocksPort 9050" and "SocksPort 10", but not "# SocksPort 192.168.0.1"
        socks_port_pattern = re.compile(rf"^#*\s*{socks_port_parameter}(?!\s*\d{{1,3}}\.\d{{1,3}}).*$")
        socks_port_replacement = f"{socks_port_parameter} {socks_port}"
        torrc_modify_line(socks_port_pattern, socks_port_replacement, torrc_lines)

    if tor_control_port:
        logging.info(f"Setting torrc {control_port_parameter} value to {tor_control_port}")
        control_port_pattern = re.compile(rf"^#*\s*{control_port_parameter}.*$")
        control_port_replacement = f"{control_port_parameter} {tor_control_port}"
        torrc_modify_line(control_port_pattern, control_port_replacement, torrc_lines)

    if tor_control_port_password or auto_generate_password:
        logging.info(f"Setting torrc {control_port_password_parameter} value{auto_generate_password*' automatically'}.")
        # Auto-generate random password and save it as environmental variable
        if auto_generate_password:
            os.environ["TOR_CONTROL_PORT_PASSWORD"] = "".join(random.choices(
                population=string.ascii_uppercase + string.digits,
                k=8))
        else:
            os.environ["TOR_CONTROL_PORT_PASSWORD"] = tor_control_port_password
        control_port_password_hash = tor_get_password_hash(os.environ.get("TOR_CONTROL_PORT_PASSWORD"),
                                                           tor_process_name)
        control_port_password_pattern = re.compile(rf"^#*\s*{control_port_password_parameter}.*$")
        control_port_password_replacement = f"{control_port_password_parameter} {control_port_password_hash}"
        torrc_modify_line(control_port_password_pattern, control_port_password_replacement, torrc_lines)

    return


def tor_setup(socks_port: (int, str), tor_control_port: (int, str), tor_control_port_password: str,
              auto_generate_password: bool, torrc_path: str, tor_process_name: str,
              localhost_ip: str, ip_api_url: str) -> bool:
    """
    Setup and check tor.
    
    :param socks_port: Port to assign to socks5/tor.
    :param tor_control_port: Port to assign to tor control.
    :param tor_control_port_password: Password to set to tor control port.
    :param auto_generate_password: Auto-generate tor control port password and save to environmental variables.
    :param torrc_path: torrc (tor config file) path.
    :param tor_process_name: Tor process name to be called from command line.
    :param localhost_ip: IP of localhost.
    :param ip_api_url: URL of some API service that returns caller IP.
    :return: True if successful, False if not.
    """

    logging.info("Reading existing torrc file.")
    try:
        with open(torrc_path, "r", encoding="utf-8") as torrc:
            torrc_lines = torrc.readlines()
    except Exception as exception:
        log_string = f"While trying to read torrc file, " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)

    logging.info("Modifying torrc lines.")
    try:
        torrc_set_values(                       # Change default values to change tor settings.
            torrc_lines=torrc_lines,
            socks_port=socks_port,
            tor_control_port=tor_control_port,
            tor_process_name=tor_process_name,
            tor_control_port_password=tor_control_port_password,
            auto_generate_password=auto_generate_password)

    except Exception as exception:
        log_string = f"While trying to modify torrc lines, " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)

    logging.info("Writing modified torrc file to disk.")
    try:
        with open(torrc_path, "w", encoding="utf-8") as torrc:
            torrc.writelines(torrc_path)
    except Exception as exception:
        log_string = f"While trying to write the modified torrc file to disk, " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)

    logging.info("Committing new torrc settings.")
    try:
        tor_processes = [process for process in psutil.process_iter() if process.name() == tor_process_name]
        if tor_processes:
            logging.info("tor services already running. Resetting...")
            for process in tor_processes:
                kill_process(process.name())

        logging.info("Starting new tor service.")
        subprocess.run(["service",  tor_process_name, "start"])
    except Exception as exception:
        log_string = f"While trying to start tor service with new configuration, " \
                     f"{type(exception).__name__} occurred: {exception}."
        logging.exception(log_string)

    logging.info("Checking if tor is active.")
    if tor_check_status(int(tor_control_port), tor_control_port_password, localhost_ip):
        logging.info("Tor service running and socket available.")
    if get_ip(ip_api_url, tor=False) == get_ip(ip_api_url, localhost_ip, int(socks_port), tor=True):
        logging.warning("Tor IP is the same as the true IP.")
        return False
    else:
        logging.info("Tor IP is different than the true IP. Success!")
    return True


if __name__ == "__main__":

    # Logger
    logging.basicConfig(
        filename=f"tor_setup_{date.today().strftime('%Y-%m-%d')}.log",
        format="{asctime}|{funcName}|{levelname}:{message}",
        style="{",
        level=logging.DEBUG)

    logging.info("Tor setup script started!")

    # Argument parsing
    script_description = "Script to setup tor."

    parser = argparse.ArgumentParser(description=script_description)
    parser.add_argument("--SocksPort", type=int, help="Port to assign to socks5/tor.",
                        default=9050, metavar="PORT")
    parser.add_argument("--TorControlPort", type=int, help="Port to assign to tor control commands.",
                        default=9051, metavar="PORT")
    parser.add_argument("--TorControlPortPassword", help="Password to set to tor control port.",
                        default="", metavar="PASS")
    parser.add_argument("--AutoGeneratePassword", action="store_true", default=False,
                        help=f"Auto-generate tor control port password and save it to environmental variable called "
                             f"'TOR_CONTROL_PORT_PASSWORD'. Overrides TorControlPortPassword.")
    parser.add_argument("--TorrcPath", help="Tor config file (torrc) path.",
                        default="/etc/tor/torrc", metavar="/PATH")
    parser.add_argument("--TorProcessName", help="Tor process name to be called from command line.",
                        default="tor", metavar="NAME")
    parser.add_argument("--LocalhostIp", help="IP of localhost.",
                        default="127.0.0.1", metavar="x.x.x.x")
    parser.add_argument("--IpApiUrl", help="URL of some API service that returns caller IP.",
                        metavar="URL", default="https://api.ipify.org")

    script_input = parser.parse_args()

    # Tor setup
    status = tor_setup(
        socks_port=script_input.SocksPort,
        tor_control_port=script_input.TorControlPort,
        tor_control_port_password=script_input.TorControlPortPassword,
        auto_generate_password=script_input.AutoGeneratePassword,
        torrc_path=script_input.TorrcPath,
        tor_process_name=script_input.TorProcessName,
        localhost_ip=script_input.LocalhostIp,
        ip_api_url=script_input.IpApiUrl)

    outcome = "SUCCESS" if status else "FAILURE"
    logging.info(f"Tor setup script finished with {outcome}!")
