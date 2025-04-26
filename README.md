# SkTorrent Batch Torrent Downloader

This Python script automates the batch downloading of `.torrent` files from the SkTorrent website **without being logged in**. <br> 
It reads a list of torrent detail page URLs from `input.txt`, extracts the actual download links, and saves the `.torrent` files to a folder.

---

## Features

- Automatically checks and installs required dependencies (`requests`, `bs4`, `tqdm`)
- Downloads `.torrent` files without cookies
- Logs all activities and errors to log file
- Retries failed HTTP requests up to 3 times
- Parralel downloading via configurable workers (By default set to 1)
- Removes duplicates URLs from input file
- Only downloads valid Sktorrent URLs
- Skips already downloaded files
- Cleans up filenames to be compatible with most operating systems

---

## Requirements

- Python 3.x

---

## Setup

1. **Clone or download this repository.**

2. **Install dependencies (optional):**

   You can manually install the dependencies, or let the script install them automatically:
   ```bash
   pip install requests beautifulsoup4
   ```

3. **Prepare `input.txt`:**

   Create or edit the `input.txt` file and paste SkTorrent **detail page** URLs (not the direct download links), one per line:
   ```
   https://sktorrent.eu/torrent/details.php?id=your_torrent_id_here
   ```

   > 💡 Tip: You can use Chrome extensions like [CopyTab URLs](https://chromewebstore.google.com/detail/copytab-urls/lolhdpcjpflggojkdoamneplianpomnl?hl=en) to copy all open tabs from Sktorrent at once. 

4. **Run the script:**
   ```bash
   python Sktorrent_bulk_downloader.py
   ```

---

## Output

- Downloaded `.torrent` files will be saved to the `downloaded_files/` folder.
- A log file will contain detailed activity and error information.

---

## Customization

You can change default settings (e.g. download folder, log file name, base URL) directly in the Python file. Look for the `CONFIGURATION` section at the top of the script.

---

## Notes

- Only links containing a download button with the `title="Stiahnut"` will work.
- The script skips invalid, broken, or non-SkTorrent links.
- Empty lines in `input.txt` are ignored.
