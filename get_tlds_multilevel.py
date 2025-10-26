#!/usr/bin/env python3
"""
Multi-Level TLD Scraper using Selenium
Usage: python3 get_tlds_multilevel.py --input source.txt --level 3
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
import tldextract
import datetime
import time
import argparse
import sys
import os
from collections import deque
import threading

class MultiLevelTLDScraper:
    def __init__(self, level=3):
        self.level = level
        self.driver = self.setup_driver()
        self.all_tlds = set()
        self.visited_urls = set()
        self.lock = threading.Lock()
        
    def setup_driver(self):
        """Setup and configure Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            sys.exit(1)

    def read_urls_from_file(self, filename):
        """Read URLs from input file, skipping comments and empty lines"""
        urls = []
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)
            return urls
        except FileNotFoundError:
            print(f"Error: Input file '{filename}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

    def extract_tld_from_url(self, url):
        """Extract TLD from a URL using tldextract"""
        try:
            extracted = tldextract.extract(url)
            domain_parts = [extracted.domain, extracted.suffix]
            tld = '.'.join(part for part in domain_parts if part)
            return tld.lower() if tld else None
        except Exception as e:
            print(f"Error extracting TLD from {url}: {e}")
            return None

    def scrape_urls_from_website(self, url):
        """Scrape all URLs from a given website"""
        found_urls = set()
        
        try:
            print(f"  Scraping: {url}")
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            # Find all anchor tags with href attributes
            links = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and href.startswith(('http://', 'https://')):
                        found_urls.add(href)
                except Exception as e:
                    continue
                    
        except TimeoutException:
            print(f"  Timeout loading: {url}")
        except WebDriverException as e:
            print(f"  Error accessing {url}: {e}")
        except Exception as e:
            print(f"  Unexpected error with {url}: {e}")
        
        return found_urls

    def multi_level_scrape(self, start_urls):
        """Perform multi-level scraping starting from initial URLs"""
        queue = deque()
        
        # Add initial URLs at level 0
        for url in start_urls:
            tld = self.extract_tld_from_url(url)
            if tld:
                self.all_tlds.add(tld)
            queue.append((url, 0))
            self.visited_urls.add(url)
        
        print(f"Starting multi-level scraping (level {self.level})...")
        print(f"Initial URLs: {len(start_urls)}")
        
        while queue:
            current_url, current_level = queue.popleft()
            
            if current_level >= self.level:
                continue
                
            print(f"Level {current_level + 1}: Processing {current_url}")
            
            # Scrape URLs from current page
            found_urls = self.scrape_urls_from_website(current_url)
            
            # Process found URLs
            new_urls_count = 0
            for url in found_urls:
                if url not in self.visited_urls:
                    self.visited_urls.add(url)
                    
                    # Extract and store TLD
                    tld = self.extract_tld_from_url(url)
                    if tld:
                        self.all_tlds.add(tld)
                    
                    # Add to queue for next level if not at max level
                    if current_level + 1 < self.level:
                        queue.append((url, current_level + 1))
                        new_urls_count += 1
            
            print(f"  Found {len(found_urls)} URLs, {new_urls_count} new URLs for next level")
            print(f"  Total unique TLDs so far: {len(self.all_tlds)}")
            print(f"  Queue size: {len(queue)}")

    def ensure_directory_exists(self, filepath):
        """Ensure the directory for the file exists"""
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

    def save_tlds_to_file(self, filename, input_file, total_urls_processed):
        """Save TLDs to a text file in Linux hosts format with custom header"""
        try:
            # Ensure the directory exists
            self.ensure_directory_exists(filename)
            
            with open(filename, 'w', encoding='utf-8') as file:
                # Write header information
                file.write("# Linux hosts file generated by Multi-Level TLD Scraper\n")
                file.write(f"# Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write(f"# Input file: {input_file}\n")
                file.write(f"# URLs processed: {total_urls_processed}\n")
                file.write(f"# Scraping level: {self.level}\n")
                file.write(f"# Unique TLDs found: {len(self.all_tlds)}\n")
                file.write(f"# Total URLs visited: {len(self.visited_urls)}\n")
                file.write("# \n")
                
                # Standard hosts file entries
                file.write("127.0.0.1 localhost\n")
                file.write("127.0.0.1 localhost.localdomain\n")
                file.write("127.0.0.1 local\n")
                file.write("255.255.255.255 broadcasthost\n")
                file.write("::1 localhost\n")
                file.write("::1 ip6-localhost\n")
                file.write("::1 ip6-loopback\n")
                file.write("fe80::1%lo0 localhost\n")
                file.write("ff00::0 ip6-localnet\n")
                file.write("ff00::0 ip6-mcastprefix\n")
                file.write("ff02::1 ip6-allnodes\n")
                file.write("ff02::2 ip6-allrouters\n")
                file.write("ff02::3 ip6-allhosts\n")
                file.write("0.0.0.0 0.0.0.0\n")
                file.write("\n")
                file.write("# Custom host records are listed here.\n")
                file.write("\n")
                file.write("\n")
                file.write("# End of custom host records.\n")
                file.write("\n")
                file.write("#=====================================\n")
                file.write("# Title: Hosts contributed by Mous B\n")
                file.write("#=====================================\n")
                file.write("\n")
                
                # Write TLDs in hosts file format using 0.0.0.0
                for tld in sorted(self.all_tlds):
                    file.write(f"0.0.0.0 {tld}\n")
                
                file.write("\n# End of generated hosts file\n")
            
            print(f"Hosts file saved to: {filename}")
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Multi-level TLD scraper using Selenium')
    parser.add_argument('--input', required=True, help='Input file containing URLs (one per line)')
    parser.add_argument('--level', type=int, default=3, help='Scraping depth level (default: 3)')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    print("Multi-Level TLD Scraper")
    print("=" * 50)
    print(f"Input file: {args.input}")
    print(f"Scraping level: {args.level}")
    print("=" * 50)
    
    # Initialize scraper
    scraper = MultiLevelTLDScraper(level=args.level)
    
    try:
        # Read input URLs
        urls_to_scrape = scraper.read_urls_from_file(args.input)
        if not urls_to_scrape:
            print("No valid URLs found to scrape. Exiting.")
            return
        
        print(f"Found {len(urls_to_scrape)} initial URLs to process")
        
        # Perform multi-level scraping
        scraper.multi_level_scrape(urls_to_scrape)
        
        # Save results
        if scraper.all_tlds:
            output_filename = os.path.join(
                "categories", 
                "porn", 
                f"multilevel_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_hosts"
            )
            
            if scraper.save_tlds_to_file(output_filename, args.input, len(scraper.visited_urls)):
                print(f"\nProcess completed!")
                print(f"Total URLs visited: {len(scraper.visited_urls)}")
                print(f"Unique TLDs found: {len(scraper.all_tlds)}")
                print(f"Output file: {output_filename}")
                print(f"Total block entries: {len(scraper.all_tlds) * 2}")
            else:
                print("Error saving results")
        else:
            print("No TLDs found.")
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    finally:
        # Always close the driver
        scraper.close()

if __name__ == "__main__":
    main()
