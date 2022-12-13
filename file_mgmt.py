import config

import csv
import os
import requests
from time import strptime, strftime


def check_dir_structure(portal_dir: str) -> None:
    """
    Makes sure the necessary folder structure is created.

    :param portal_dir: Portal root directory
    :return: None
    """
    if not os.path.exists(portal_dir):
        os.makedirs(portal_dir)
    if not os.path.exists(os.path.join(portal_dir, config.REQUESTS_ARCHIVE_DIR)):
        os.makedirs(os.path.join(portal_dir, config.REQUESTS_ARCHIVE_DIR))

    return


def save_request(req: requests.models.Response, dir_path: str) -> None:
    """
    Saves a request object to disk as textfile for archiving.

    :param req: requests.models.Response object
    :param dir_path: Directory path, where the request should be archived
    :return: None
    """
    request_elements = [
        "request method: " + req.request.method,
        "request url: " + req.request.url,
        "headers: " + "   ".join("{}: {}".format(key, value) for key, value in req.request.headers.items()),
        "status: " + str(req.status_code),
        "reason:  " + req.reason,
        "",
        req.text]

    request_save_text = "\n".join(request_elements)
    request_time = strptime(req.headers["Date"], "%a, %d %b %Y %H:%M:%S %Z")
    request_time_string = strftime("%Y%m%d_%H%M%S", request_time)
    request_save_path = os.path.join(dir_path, "REQUEST_" + request_time_string + "GMT.txt")

    with open(request_save_path, "w") as file:
        file.write(request_save_text)

    return


def save_requests_to_txt(req: list | requests.models.Response, dir_path: str) -> None:
    """
    Wrapper around save_request to handle both lists and single objects in req input
    :param req: List of requests.models.Response objects or a single object
    :param dir_path: Directory path, where the requests should be archived
    :return: None
    """
    req = req if isinstance(req, list) else [req]
    for request in req:
        save_request(request, dir_path)
    return


def write_data_csv(data: list, path: str, replace: bool = False) -> None:
    """
    Writes processed data to csv.
    Pulls the column names from the keys of first data row.
    If mode="create", creates a new csv. Otherwise, appends to existing one.

    :param data: List of dictionaries (rows)
    :param path: Path to save the csv to
    :param replace: If True, a new file is created. Otherwise, data is appended to existing file.
    :return:
    """
    save_mode = "w" if replace else "a"
    with open(path, save_mode) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[field for field in data[0].keys()])
        if replace:
            writer.writeheader()
        for row in data:
            writer.writerow(row)

    return


def get_dir_size_mb(dir_path: str) -> float:
    """
    Calculates total size of a directory.
    Only handles directories that don't have subdirectories.

    :param dir_path: Path of directory to analyze
    :return: Folder size in megabytes
    """
    total_size_mb = sum([file.stat().st_size for file in os.scandir(dir_path)]) / (10 ** 6)
    return total_size_mb


def remove_oldest_file(dir_path: str) -> None:
    """
    Removes the file in directory that was modified first (the longest time ago)
    :param dir_path: Directory where the file should be removed
    :return: None
    """
    oldest_file = sorted(os.scandir(dir_path), key=lambda x: x.stat().st_mtime)[0]
    os.remove(oldest_file)
    return
