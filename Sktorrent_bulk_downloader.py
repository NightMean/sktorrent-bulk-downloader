# This Python script is used for batch downloading torrent files from SkTorrent from input.txt file

import os
import subprocess
import importlib
import argparse
import time
import logging
from urllib.parse import urljoin, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor
import re
from threading import Lock

# ========== CONFIGURATION ===========

BASE_URL = "https://sktorrent.eu/torrent/"
INPUT_FILE = "input.txt"
DOWNLOAD_FOLDER = "downloaded_files"
LOG_FILE = "download.log"
MAX_RETRIES = 3
RETRY_DELAY = 2  # Seconds to wait between retries
REQUIRED_LIBRARIES = ['requests', 'bs4', 'tqdm']
VALID_DOMAIN = "sktorrent.eu"
MAX_WORKERS = 4  # Number of concurrent download threads

# Thread-safe logging
logging_lock = Lock()

# ========== FUNCTIONS ===========

def sanitize_filename(filename):
    """Sanitize filenames by replacing special characters with underscores."""
    return re.sub(r'[\/:*?"<>|]', '_', filename)

def ensure_libraries_installed():
    """Check if required libraries are installed, and install them if not."""
    for library in REQUIRED_LIBRARIES:
        try:
            importlib.import_module(library)
        except ImportError:
            print(f"Library '{library}' is not installed. Attempting to install...")
            with logging_lock:
                logging.warning(f"Attempting to install {library}...")
            try:
                subprocess.check_call(['pip', 'install', library])
                print(f"Successfully installed {library}.")
                with logging_lock:
                    logging.info(f"Successfully installed {library}.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {library}. Error: {e}")
                with logging_lock:
                    logging.error(f"Failed to install {library}. Error: {e}")
                raise ImportError(f"Could not install {library}. Please install it manually with 'pip install {library}'.")
    
    # Delayed imports after ensuring installation
    global requests, BeautifulSoup, tqdm
    import requests
    from bs4 import BeautifulSoup
    from tqdm import tqdm

def setup_environment(download_folder):
    """Prepare folders and input file."""
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

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

def is_valid_sktorrent_url(url):
    """Check if the URL contains sktorrent.eu/."""
    return url.strip() and 'sktorrent.eu/' in url

def print_above_progress(*args, **kwargs):
    """Print messages above the progress bar by first clearing the current line."""
    tqdm.write(" ".join(str(arg) for arg in args), **kwargs)

def download_from_url(url, index, total, download_folder):
    """Handle fetching and downloading torrents from a SkTorrent detail page URL."""
    print_above_progress(f"\nProcessing file {index} of {total}...")
    url = url.strip()

    for retry in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            break
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            with logging_lock:
                logging.warning(f"Failed to fetch URL: {url}. Retrying attempt {retry + 1}...")
            time.sleep(RETRY_DELAY)
    else:
        with logging_lock:
            logging.error(f"Failed to fetch URL: {url}. Max retries exceeded.")
        return False

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        download_link = soup.find("a", title="Stiahnut")

        if download_link:
            download_url = urljoin(BASE_URL, download_link["href"])
            with logging_lock:
                logging.info(f"Download URL: {download_url}")

            filename_encoded = download_url.split("&f=")[-1].split("&")[0]
            filename = unquote(filename_encoded)
            sanitized_filename = sanitize_filename(filename)

            file_path = os.path.join(download_folder, sanitized_filename)

            if os.path.exists(file_path):
                print_above_progress(f"SKIPPED (Already exists): {sanitized_filename}")
                with logging_lock:
                    logging.info(f"Skipped {sanitized_filename} (Already downloaded)")
            else:
                for retry in range(MAX_RETRIES):
                    try:
                        download_response = requests.get(download_url, timeout=10, stream=True)
                        total_size = int(download_response.headers.get('content-length', 0))
                        
                        # Create download progress bar
                        with open(file_path, "wb") as torrent_file, tqdm(
                            total=total_size,
                            unit='B',
                            unit_scale=True,
                            desc=f"Downloading {index}/{total}",
                            leave=False,
                            position=1,  # Use position 1 to avoid conflict with main progress bar
                            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'
                        ) as chunk_pbar:
                            for chunk in download_response.iter_content(chunk_size=8192):
                                torrent_file.write(chunk)
                                chunk_pbar.update(len(chunk))
                        
                        # Print downloaded message
                        print_above_progress(f"Downloaded: {sanitized_filename}")
                        break
                    except (requests.exceptions.RequestException, requests.exceptions.Timeout):
                        with logging_lock:
                            logging.warning(f"Failed to download {sanitized_filename}. Retrying attempt {retry + 1}...")
                        time.sleep(RETRY_DELAY)
                else:
                    with logging_lock:
                        logging.error(f"Failed to download {sanitized_filename}. Max retries exceeded.")
                    print_above_progress(f"ERROR: (Could not download): {sanitized_filename}")
                    return False

                if download_response.status_code == 200:
                    with logging_lock:
                        logging.info(f"Downloaded {sanitized_filename} to {download_folder}")
                else:
                    with logging_lock:
                        logging.error(f"Failed to download {sanitized_filename}")
                    print_above_progress(f"ERROR: (Could not download): {sanitized_filename}")
                    return False
        else:
            with logging_lock:
                logging.error(f"Download link not found on page: {url}")
            return False
    else:
        with logging_lock:
            logging.error(f"Failed to fetch URL: {url} with status code {response.status_code}")
        return False
    return True

# ========== MAIN ===========

def main():
    global DOWNLOAD_FOLDER
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Download torrents from SkTorrent.")
    parser.add_argument('--output-dir', default=DOWNLOAD_FOLDER, help="Directory to save downloaded files")
    args = parser.parse_args()
    DOWNLOAD_FOLDER = args.output_dir

    setup_logging()
    ensure_libraries_installed()
    setup_environment(DOWNLOAD_FOLDER)

    with open(INPUT_FILE, "r") as input_file:
        # Read lines, strip whitespace, ignore empty lines, remove duplicates
        all_urls = list(set(url.strip() for url in input_file.readlines() if url.strip()))
        original_url_count = sum(1 for line in open(INPUT_FILE, "r") if line.strip())
        removed_duplicates = original_url_count - len(all_urls)
        if removed_duplicates > 0:
            with logging_lock:
                logging.info(f"Removed {removed_duplicates} duplicate URLs.")

        valid_urls = [url for url in all_urls if is_valid_sktorrent_url(url)]
        invalid_urls = [url for url in all_urls if not is_valid_sktorrent_url(url)]

    total_valid_urls = len(valid_urls)
    total_invalid_urls = len(invalid_urls)

    with logging_lock:
        logging.info(f"Found {total_valid_urls} valid sktorrent.eu URLs.")
        logging.info(f"Found {total_invalid_urls} invalid URLs.")
        for url in invalid_urls:
            logging.info(f"Invalid URL skipped: {url}")

    print(f"Found {total_valid_urls} valid sktorrent.eu URLs to process.")
    if total_invalid_urls > 0:
        print(f"Found {total_invalid_urls} invalid URLs (will be skipped).")
    if removed_duplicates > 0:
        print(f"Removed {removed_duplicates} duplicate URLs.\n")

    valid_url_count = 0
    invalid_url_count = total_invalid_urls  # Pre-count invalid URLs

    def download_wrapper(args):
        url, idx, total = args
        return download_from_url(url, idx, total, DOWNLOAD_FOLDER)

    if valid_urls:
        # Main progress bar for overall processing (position=0)
        with tqdm(total=total_valid_urls, desc="Processing URLs", position=0, leave=True) as main_pbar:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                results = []
                for result in executor.map(download_wrapper, [(url, idx, total_valid_urls) for idx, url in enumerate(valid_urls, start=1)]):
                    results.append(result)
                    main_pbar.update(1)
        
        valid_url_count = sum(1 for result in results if result)
        invalid_url_count += sum(1 for result in results if not result)

    print("\nSummary:")
    print(f"Valid sktorrent.eu URLs processed: {valid_url_count}")
    print(f"Invalid URLs (non-sktorrent.eu or failed): {invalid_url_count}")

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
