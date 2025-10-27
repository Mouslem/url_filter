#!/usr/bin/env python3
"""
Multi-Level TLD Scraper using Selenium with Firefox/GeckoDriver
Usage: python3 get_tlds_multilevel_firefox.py --input source.txt --level 3 --threads 5
"""

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
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
import queue as thread_queue

class MultiLevelTLDScraperFirefox:
    def __init__(self, level=3, max_workers=5, geckodriver_path=None):
        self.level = level
        self.max_workers = max_workers
        self.geckodriver_path = geckodriver_path
        self.all_tlds = set()
        self.visited_urls = set()
        self.visited_lock = threading.Lock()
        self.tlds_lock = threading.Lock()
        self.stats = {
            'urls_processed': 0,
            'urls_found': 0,
            'errors': 0
        }
        self.stats_lock = threading.Lock()
        self.driver = None  # Single driver for single-threaded mode
        
    def setup_driver(self):
        """Setup and configure Firefox driver"""
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--disable-gpu")
        
        # Set user agent to avoid detection
        firefox_options.set_preference("general.useragent.override", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
        
        # Disable images for faster loading
        firefox_options.set_preference("permissions.default.image", 2)
        firefox_options.set_preference("dom.ipc.plugins.enabled.libflashplayer", False)
        
        try:
            if self.geckodriver_path:
                service = Service(executable_path=self.geckodriver_path)
                driver = webdriver.Firefox(service=service, options=firefox_options)
            else:
                driver = webdriver.Firefox(options=firefox_options)
            
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            print(f"Error setting up Firefox driver: {e}")
            print("Please ensure:")
            print("1. Firefox is installed")
            print("2. GeckoDriver is installed and in your PATH")
            print("3. Or specify GeckoDriver path with --geckodriver-path")
            return None

    def get_driver(self):
        """Get the driver instance"""
        if not self.driver:
            self.driver = self.setup_driver()
        return self.driver

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
        """Scrape all URLs from a given website using Firefox"""
        driver = self.get_driver()
        if not driver:
            return set()
            
        found_urls = set()
        
        try:
            print(f"  Scraping: {url}")
            driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            # Find all anchor tags with href attributes
            links = driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and href.startswith(('http://', 'https://')):
                        found_urls.add(href)
                except Exception as e:
                    continue
                    
        except TimeoutException:
            print(f"  Timeout loading: {url}")
            with self.stats_lock:
                self.stats['errors'] += 1
        except WebDriverException as e:
            print(f"  Error accessing {url}: {e}")
            with self.stats_lock:
                self.stats['errors'] += 1
        except Exception as e:
            print(f"  Unexpected error with {url}: {e}")
            with self.stats_lock:
                self.stats['errors'] += 1
        
        return found_urls

    def multi_level_scrape(self, start_urls):
        """Perform multi-level scraping with simplified threading"""
        queue = deque()
        
        # Add initial URLs at level 0
        for url in start_urls:
            tld = self.extract_tld_from_url(url)
            if tld:
                with self.tlds_lock:
                    self.all_tlds.add(tld)
            queue.append((url, 0))
            self.visited_urls.add(url)
        
        print(f"Starting multi-level scraping (level {self.level}) with Firefox...")
        print(f"Initial URLs: {len(start_urls)}")
        
        while queue:
            current_url, current_level = queue.popleft()
            
            if current_level >= self.level:
                continue
                
            print(f"Level {current_level + 1}: Processing {current_url}")
            
            # Update stats
            with self.stats_lock:
                self.stats['urls_processed'] += 1
                processed = self.stats['urls_processed']
            
            print(f"L{current_level+1} [{processed} processed]: {current_url[:60]}...")
            
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
                        with self.tlds_lock:
                            self.all_tlds.add(tld)
                    
                    # Add to queue for next level if not at max level
                    if current_level + 1 < self.level:
                        queue.append((url, current_level + 1))
                        new_urls_count += 1
            
            # Update found URLs count
            with self.stats_lock:
                self.stats['urls_found'] += len(found_urls)
            
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
                file.write("# Linux hosts file generated by Multi-Level TLD Scraper (Firefox)\n")
                file.write(f"# Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write(f"# Input file: {input_file}\n")
                file.write(f"# URLs processed: {total_urls_processed}\n")
                file.write(f"# Scraping level: {self.level}\n")
                file.write(f"# Browser: Firefox/GeckoDriver\n")
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
                    file.write(f"0.0.0.0 www.{tld}\n")
                
                file.write("\n# End of generated hosts file\n")
            
            print(f"Hosts file saved to: {filename}")
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                print("Firefox driver closed")
            except:
                pass

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Multi-level TLD scraper using Firefox/GeckoDriver')
    parser.add_argument('--input', required=True, help='Input file containing URLs (one per line)')
    parser.add_argument('--level', type=int, default=3, help='Scraping depth level (default: 3)')
    parser.add_argument('--threads', type=int, default=1, help='Number of threads (default: 1)')
    parser.add_argument('--geckodriver-path', help='Path to GeckoDriver executable (optional)')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    print("Multi-Level TLD Scraper (Firefox/GeckoDriver)")
    print("=" * 60)
    print(f"Input file: {args.input}")
    print(f"Scraping level: {args.level}")
    print(f"Threads: {args.threads}")
    if args.geckodriver_path:
        print(f"GeckoDriver path: {args.geckodriver_path}")
    print("=" * 60)
    
    # Initialize scraper
    scraper = MultiLevelTLDScraperFirefox(
        level=args.level, 
        max_workers=args.threads,
        geckodriver_path=args.geckodriver_path
    )
    
    try:
        # Read input URLs
        urls_to_scrape = scraper.read_urls_from_file(args.input)
        if not urls_to_scrape:
            print("No valid URLs found to scrape. Exiting.")
            return
        
        print(f"Found {len(urls_to_scrape)} initial URLs to process")
        
        # Perform multi-level scraping
        start_time = time.time()
        scraper.multi_level_scrape(urls_to_scrape)
        end_time = time.time()
        
        # Calculate statistics
        total_time = end_time - start_time
        urls_per_second = scraper.stats['urls_processed'] / total_time if total_time > 0 else 0
        
        # Save results
        if scraper.all_tlds:
            output_filename = os.path.join(
                "categories", 
                "porn", 
                f"firefox_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_hosts.txt"
            )
            
            if scraper.save_tlds_to_file(output_filename, args.input, scraper.stats['urls_processed']):
                print(f"\nProcess completed!")
                print(f"Total time: {total_time:.2f} seconds")
                print(f"URLs processed: {scraper.stats['urls_processed']}")
                print(f"URLs per second: {urls_per_second:.2f}")
                print(f"Unique TLDs found: {len(scraper.all_tlds)}")
                print(f"Errors encountered: {scraper.stats['errors']}")
                print(f"Output file: {output_filename}")
            else:
                print("Error saving results")
        else:
            print("No TLDs found.")
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always close driver
        scraper.close()

if __name__ == "__main__":
    main()


