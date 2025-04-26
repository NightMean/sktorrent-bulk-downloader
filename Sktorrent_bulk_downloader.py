# This python scripts is used for batch downloading torrent files from SkTorrent from input.txt file

import os
import requests
import subprocess
import importlib
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import re
import logging

# Function to sanitize the filename by replacing special characters with underscores
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '_', filename)

# Base URL of the site
base_url = "https://sktorrent.eu/torrent/"

# List of required libraries
required_libraries = ['requests', 'bs4']

# Configure logging
log_file = "download.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if each library is installed
for library in required_libraries:
    try:
        importlib.import_module(library)
    except ImportError:
        logging.error(f"{library} is not installed. Installing...")
        subprocess.check_call(['pip', 'install', library])
    else:
        pass  # Don't log "already installed" every time

# Create the 'downloaded_files' folder if it doesn't exist
download_folder = "downloaded_files"
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

# Check if the input.txt file exists, and create it if not
if not os.path.exists("input.txt"):
    with open("input.txt", "w") as input_file:
        input_file.write("")

# Read the list of URLs from input.txt
with open("input.txt", "r") as input_file:
    urls = input_file.readlines()

# Set maximum number of retries
max_retries = 3

# Process each URL
for url in urls:
    url = url.strip()  # Remove leading/trailing whitespace

    # Send an HTTP GET request to the URL with retries and timeout
    for retry in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            break
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            logging.warning(f"Failed to fetch URL: {url}. Retrying attempt {retry + 1}...")
    else:
        logging.error(f"Failed to fetch URL: {url}. Max retries exceeded.")
        continue

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the download link within the HTML
        download_link = soup.find("a", title="Stiahnut")

        if download_link:
            download_url_relative = download_link["href"]
            download_url = urljoin(base_url, download_url_relative)
            logging.info(f"Download URL: {download_url}")

            # Extract the filename from the download URL and decode special characters
            filename_encoded = download_url.split("&f=")[-1].split("&")[0]
            filename = unquote(filename_encoded)
            sanitized_filename = sanitize_filename(filename)
            logging.info(f"Filename: {sanitized_filename}")

            # Check if the file already exists in the 'downloaded_files' folder
            file_path = os.path.join(download_folder, sanitized_filename)
            if os.path.exists(file_path):
                print(f"SKIPPED (Already exists): {sanitized_filename}")
                logging.info(f"Skipped {sanitized_filename} (Already downloaded)")
            else:
                # Send an HTTP GET request to the download URL
                for retry in range(max_retries):
                    try:
                        download_response = requests.get(download_url, timeout=10)
                        break
                    except (requests.exceptions.RequestException, requests.exceptions.Timeout):
                        logging.warning(f"Failed to download {sanitized_filename}. Retrying attempt {retry + 1}...")
                else:
                    logging.error(f"Failed to download {sanitized_filename}. Max retries exceeded.")
                    print(f"ERROR: (Could not download): {sanitized_filename}")
                    continue

                # Check if the download request was successful (status code 200)
                if download_response.status_code == 200:
                    # Save the downloaded file in the 'downloaded_files' folder
                    with open(file_path, "wb") as torrent_file:
                        torrent_file.write(download_response.content)
                    print(f"Downloaded: {sanitized_filename}")
                    logging.info(f"Downloaded {sanitized_filename} to {download_folder}")
                else:
                    logging.error(f"Failed to download {sanitized_filename}")
                    print(f"ERROR: (Could not download): {sanitized_filename}")
        else:
            logging.error("Download link not found on the page.")
    else:
        logging.error(f"Failed to fetch URL: {url}")
