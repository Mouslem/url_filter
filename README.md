# TLD Scraper

A Selenium-based web scraper that extracts Top Level Domains (TLDs) from websites and generates Linux hosts files for domain blocking.

## Description

`get_tlds.py` is a Python script that automates the process of discovering and blocking potentially unwanted domains. It visits specified websites, scrapes all links, extracts TLDs, and generates a formatted hosts file ready for use on Linux systems.

## Features

- **Input Processing**: Reads URLs from input file (one per line), automatically skipping comments starting with `#`
- **Web Scraping**: Uses Selenium with headless Chrome to visit each URL and extract all links
- **TLD Extraction**: Parses found URLs to extract Top Level Domains
- **Duplicate Removal**: Automatically removes duplicate domains
- **Hosts File Generation**: Creates properly formatted Linux hosts files
- **Automatic Directory Creation**: Creates required directory structure if it doesn't exist

## Output

- **Location**: `url_filter/categories/porn/`
- **Filename Format**: `YYYYMMDD_HHMMSS_hosts.txt`
- **Format**: Standard Linux hosts file with:
  - Custom header information
  - Standard system entries (localhost, IPv6, etc.)
  - Domain blocking entries using `0.0.0.0`
  - Both base domains and www subdomains

## Installation

### Prerequisites

- Python 3.x
- Chrome browser
- ChromeDriver

### Dependencies

Install required packages:

```bash
pip install selenium tldextract
```

# Usage
```bash
python3 get_tlds.py --input source.txt
