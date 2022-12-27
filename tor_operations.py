import socket
import logging
import requests
import re
from time import sleep


def get_ip(ip_api_url: str, tor_host: str = "127.0.0.1", socks_port: (int, str) = 9050, tor: bool = False) -> str:
    """
    Check IP that is seen by an external service.

    :param ip_api_url: URL of some API service that returns caller IP.
    :param tor_host: IP of tor service.
    :param socks_port: Port number of the socks5 port.
    :param tor: check tor IP. False = check regular IP.
    :return: Your IP, as the external API sees it.
    """
    tor_proxies = {
        "http": f"socks5://{tor_host}:{socks_port}",
        "https": f"socks5://{tor_host}:{socks_port}"}
    try:
        if tor:
            response = requests.get(ip_api_url, proxies=tor_proxies)
        else:
            response = requests.get(ip_api_url)
        ip = response.content.decode()
        if not re.match(r"\d{1,3}\.\d{1,3}.\d{1,3}.\d{1,3}", ip):
            raise UserWarning(f"'{ip}' is not in the standard IPv4 format.")
        return ip

    except Exception as exception:
        log_string = f"While trying to check{' tor'*tor} ip, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)


def check_tor_ip(tor_host: str, socks_port: (int, str), ip_api_url: str) -> bool:
    """
    Check if IP via tor proxy is different from regular IP.

    :param tor_host: IP of tor service.
    :param socks_port: Port number of the socks5 port.
    :param ip_api_url: URL of some API service that returns caller IP.
    :return: True if tor IP is different from regular (uncovered) IP, False otherwise.
    """
    try:
        ip_over_tor = get_ip(
            ip_api_url=ip_api_url,
            tor_host=tor_host,
            socks_port=socks_port,
            tor=True)

    except Exception as exception:
        log_string = f"While trying to make a request via the tor proxy to {ip_api_url}, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        ip_over_tor = ""

    try:
        ip_regular = get_ip(ip_api_url=ip_api_url)
    except Exception as exception:
        log_string = f"While trying to make a regular request to {ip_api_url}, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)
        ip_regular = ""

    different_ip_success = ip_over_tor != ip_regular
    if different_ip_success:
        logging.info("SUCCESS. IP over tor proxy is different than regular ip.")
    else:
        logging.warning("Could not verify whether IP over tor proxy is different from regular IP.")

    return different_ip_success


def get_socket_response(socket_object: socket.socket) -> str:
    """
    Get response string from a (shut down) socket object.

    :param socket_object: A socket with a response.
    :return: Response string.
    """
    response = str()
    while True:
        data = socket_object.recv(1024)
        if not data:
            break
        response += data.decode()
    return response


def check_tor_control_port(tor_host: str, tor_control_port: (int, str)) -> bool:
    """
    Tests if tor control port is up, by sending PROTOCOLINFO command.

    :param tor_host: IP of tor service.
    :param tor_control_port: Port number of tor control port.
    :return: If response from tor control contains '250 OK', the function returns True.
    """
    control_port_socket = socket.socket()
    control_port_socket.settimeout(60)

    try:
        control_port_socket.connect((tor_host, int(tor_control_port)))
        control_port_socket.sendall("PROTOCOLINFO\r\n".encode())
        control_port_socket.shutdown(socket.SHUT_WR)
    except Exception as exception:
        log_string = f"While trying to connect to tor control port, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)

    success_pattern = re.compile("250\s*OK")
    response = get_socket_response(control_port_socket)
    return bool(success_pattern.search(response))


def tor_control_port_command(command: str, tor_host: str, tor_control_port: (int, str),
                             tor_control_port_password: str) -> str:
    """
    Send a command to tor control port.
    Additional info: https://gitweb.torproject.org/torspec.git/tree/control-spec.txt

    :param command: Command to send (e.g. SIGNAL TERM, NEWNYM etc.)
    :param tor_host: IP of tor service.
    :param tor_control_port: Port number of tor control port.
    :param tor_control_port_password: Password set to tor control port.
    :return: Control port response to the command.
    """
    control_port_socket = socket.socket()
    control_port_socket.settimeout(60)
    success_pattern = re.compile("250\s*OK")

    try:
        control_port_socket.connect((tor_host, int(tor_control_port)))
    except Exception as exception:
        log_string = f"While trying to connect to tor control port, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)

    try:
        # Password has to be in double quotes
        control_port_socket.sendall(f'AUTHENTICATE "{tor_control_port_password}"\r\n'.encode())
        authentication_response = control_port_socket.recv(1024).decode()
        if not bool(success_pattern.search(authentication_response)):
            raise UserWarning(f"Tor control port authentication failed: {authentication_response}.")
    except Exception as exception:
        log_string = f"While trying to authenticate tor control port, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)

    try:
        control_port_socket.sendall(f"{command}\r\n".encode())
        control_port_socket.shutdown(socket.SHUT_WR)
    except Exception as exception:
        log_string = f"While trying to send command {command} to tor control port, " \
                     f"{type(exception).__name__} occurred: {exception}"
        logging.exception(log_string)

    command_response = get_socket_response(control_port_socket)
    return command_response


is_tor_ip_different = check_tor_ip("172.28.5.2", 9050, "http://api.ipify.org")
is_control_port_up = check_tor_control_port("172.28.5.2", 9051)
logging.info(f"Tor IP different: {is_tor_ip_different}")
logging.info(f"Tor control port accessible: {is_control_port_up}")

logging.info(f"Original tor IP: {get_ip('http://api.ipify.org', '172.28.5.2', tor=True)}")
print(tor_control_port_command('SIGNAL NEWNYM', '172.28.5.2', 9051, 'tere'))
logging.info(f"Changed tor IP: {get_ip('http://api.ipify.org', '172.28.5.2', tor=True)}")
