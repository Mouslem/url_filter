get_tlds.py - A Selenium-based web scraper that:
    Takes an input file with URLs (one per line, skips comments starting with #)
    Visits each URL and scrapes all links from the page
    Extracts Top Level Domains (TLDs) from found URLs
    Removes duplicates
    Saves the results in a Linux hosts file format to url_filter/categories/porn/
    Uses 0.0.0.0 for blocking entries
    Includes specific headers and standard hosts file entries

Key features:
    Command line: python3 get_tlds.py --input source.txt
    Handles input files with comments (# lines)
    Creates directory structure automatically
    Output format includes standard hosts entries and custom header
    Uses Selenium with headless Chrome

Output location:
url_filter/categories/porn/YYYYMMDD_HHMMSS_hosts.txt

