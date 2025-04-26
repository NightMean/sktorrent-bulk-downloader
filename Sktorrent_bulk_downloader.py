# This Python script is used for batch downloading torrent files from SkTorrent from input.txt file

import os
import requests
import subprocess
import importlib
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import re
import logging

# ========== CONFIGURATION ==========

BASE_URL = "https://sktorrent.eu/torrent/"
INPUT_FILE = "input.txt"
DOWNLOAD_FOLDER = "downloaded_files"
LOG_FILE = "download.log"
MAX_RETRIES = 3
REQUIRED_LIBRARIES = ['requests', 'bs4']

# ========== FUNCTIONS ==========

def sanitize_filename(filename):
    """Sanitize filenames by replacing special characters with underscores."""
    return re.sub(r'[\/:*?"<>|]', '_', filename)

def ensure_libraries_installed():
    """Check if required libraries are installed, and install them if not."""
    for library in REQUIRED_LIBRARIES:
        try:
            importlib.import_module(library)
            logging.info(f"{library} is already installed.")
        except ImportError:
            logging.error(f"{library} is not installed. Installing...")
            subprocess.check_call(['pip', 'install', library])

def setup_environment():
    """Prepare folders and input file."""
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    if not os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, "w") as input_file:
            input_file.write("")  # Leave empty

def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def download_from_url(url):
    """Handle fetching and downloading torrents from a SkTorrent detail page URL."""
    url = url.strip()

    for retry in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            break
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            logging.warning(f"Failed to fetch URL: {url}. Retrying attempt {retry + 1}...")
    else:
        logging.error(f"Failed to fetch URL: {url}. Max retries exceeded.")
        return

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        download_link = soup.find("a", title="Stiahnut")

        if download_link:
            download_url = urljoin(BASE_URL, download_link["href"])
            logging.info(f"Download URL: {download_url}")

            filename_encoded = download_url.split("&f=")[-1].split("&")[0]
            filename = unquote(filename_encoded)
            sanitized_filename = sanitize_filename(filename)

            file_path = os.path.join(DOWNLOAD_FOLDER, sanitized_filename)

            if os.path.exists(file_path):
                print(f"SKIPPED (Already exists): {sanitized_filename}")
                logging.info(f"Skipped {sanitized_filename} (Already downloaded)")
            else:
                for retry in range(MAX_RETRIES):
                    try:
                        download_response = requests.get(download_url, timeout=10)
                        break
                    except (requests.exceptions.RequestException, requests.exceptions.Timeout):
                        logging.warning(f"Failed to download {sanitized_filename}. Retrying attempt {retry + 1}...")
                else:
                    logging.error(f"Failed to download {sanitized_filename}. Max retries exceeded.")
                    print(f"ERROR: (Could not download): {sanitized_filename}")
                    return

                if download_response.status_code == 200:
                    with open(file_path, "wb") as torrent_file:
                        torrent_file.write(download_response.content)
                    print(f"Downloaded: {sanitized_filename}")
                    logging.info(f"Downloaded {sanitized_filename} to {DOWNLOAD_FOLDER}")
                else:
                    logging.error(f"Failed to download {sanitized_filename}")
                    print(f"ERROR: (Could not download): {sanitized_filename}")
        else:
            logging.error(f"Download link not found on page: {url}")
    else:
        logging.error(f"Failed to fetch URL: {url} with status code {response.status_code}")

# ========== MAIN ==========

def main():
    setup_logging()
    ensure_libraries_installed()
    setup_environment()

    with open(INPUT_FILE, "r") as input_file:
        urls = input_file.readlines()

    for url in urls:
        if url.strip():  # Skip empty lines
            download_from_url(url)

if __name__ == "__main__":
    main()
