#!/usr/bin/env python3
"""
Multi-Level TLD Scraper using Selenium with Multi-threading
Usage: python3 get_tlds_multilevel_threaded.py --input source.txt --level 3 --threads 5
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
import queue as thread_queue
from concurrent.futures import ThreadPoolExecutor, as_completed

class MultiThreadedTLDScraper:
    def __init__(self, level=3, max_workers=5):
        self.level = level
        self.max_workers = max_workers
        self.all_tlds = set()
        self.visited_urls = set()
        self.visited_lock = threading.Lock()
        self.tlds_lock = threading.Lock()
        self.scraping_queue = thread_queue.Queue()
        self.drivers = {}  # Store drivers per thread
        self.stats = {
            'urls_processed': 0,
            'urls_found': 0,
            'errors': 0
        }
        self.stats_lock = threading.Lock()
        
    def setup_driver(self):
        """Setup and configure Chrome driver for a thread"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(25)  # Slightly lower timeout for threading
            return driver
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            return None

    def get_driver(self):
        """Get or create driver for current thread"""
        thread_id = threading.get_ident()
        if thread_id not in self.drivers:
            self.drivers[thread_id] = self.setup_driver()
        return self.drivers[thread_id]

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
            return None

    def scrape_urls_from_website(self, url, current_level):
        """Scrape all URLs from a given website"""
        driver = self.get_driver()
        if not driver:
            return set()
            
        found_urls = set()
        
        try:
            driver.get(url)
            time.sleep(1)  # Reduced wait time for threading
            
            # Find all anchor tags with href attributes
            links = driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and href.startswith(('http://', 'https://')):
                        found_urls.add(href)
                except Exception:
                    continue
                    
        except TimeoutException:
            with self.stats_lock:
                self.stats['errors'] += 1
        except WebDriverException:
            with self.stats_lock:
                self.stats['errors'] += 1
        except Exception:
            with self.stats_lock:
                self.stats['errors'] += 1
        
        return found_urls

    def process_url(self, url_info):
        """Process a single URL (worker function)"""
        url, current_level = url_info
        
        # Update stats
        with self.stats_lock:
            self.stats['urls_processed'] += 1
            processed = self.stats['urls_processed']
            found = self.stats['urls_found']
            errors = self.stats['errors']
        
        print(f"L{current_level+1} [{processed} processed, {found} found, {errors} errors]: {url[:60]}...")
        
        # Scrape URLs from current page
        found_urls = self.scrape_urls_from_website(url, current_level)
        
        new_urls = []
        with self.visited_lock:
            for found_url in found_urls:
                if found_url not in self.visited_urls:
                    self.visited_urls.add(found_url)
                    
                    # Extract and store TLD
                    tld = self.extract_tld_from_url(found_url)
                    if tld:
                        with self.tlds_lock:
                            self.all_tlds.add(tld)
                    
                    # Add to queue for next level if not at max level
                    if current_level + 1 < self.level:
                        new_urls.append((found_url, current_level + 1))
        
        # Update stats
        with self.stats_lock:
            self.stats['urls_found'] += len(found_urls)
        
        # Add new URLs to queue
        for new_url in new_urls:
            self.scraping_queue.put(new_url)
        
        return len(found_urls), len(new_urls)

    def multi_level_scrape(self, start_urls):
        """Perform multi-level scraping with threading"""
        # Add initial URLs to queue
        for url in start_urls:
            tld = self.extract_tld_from_url(url)
            if tld:
                with self.tlds_lock:
                    self.all_tlds.add(tld)
            self.scraping_queue.put((url, 0))
            with self.visited_lock:
                self.visited_urls.add(url)
        
        print(f"Starting multi-level scraping (level {self.level}) with {self.max_workers} threads...")
        print(f"Initial URLs: {len(start_urls)}")
        
        active_tasks = 0
        max_queue_size = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit initial batch of tasks
            futures = set()
            while not self.scraping_queue.empty() or futures:
                # Submit new tasks while we have capacity
                while len(futures) < self.max_workers and not self.scraping_queue.empty():
                    url_info = self.scraping_queue.get()
                    future = executor.submit(self.process_url, url_info)
                    futures.add(future)
                
                # Update queue stats
                current_queue_size = self.scraping_queue.qsize()
                max_queue_size = max(max_queue_size, current_queue_size)
                
                # Wait for at least one task to complete
                if futures:
                    done, futures = as_completed(futures, timeout=1), set()
                    for future in done:
                        try:
                            found_count, new_count = future.result()
                            print(f"  Progress: {len(self.all_tlds)} TLDs | Queue: {current_queue_size} | Active: {len(futures)}")
                        except Exception as e:
                            print(f"Task error: {e}")
                
                # Small delay to prevent CPU spinning
                time.sleep(0.1)

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
                file.write("# Linux hosts file generated by Multi-Threaded TLD Scraper\n")
                file.write(f"# Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write(f"# Input file: {input_file}\n")
                file.write(f"# URLs processed: {total_urls_processed}\n")
                file.write(f"# Scraping level: {self.level}\n")
                file.write(f"# Threads used: {self.max_workers}\n")
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
        """Close all WebDrivers"""
        for driver in self.drivers.values():
            try:
                if driver:
                    driver.quit()
            except:
                pass
        print("All WebDrivers closed")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Multi-threaded TLD scraper using Selenium')
    parser.add_argument('--input', required=True, help='Input file containing URLs (one per line)')
    parser.add_argument('--level', type=int, default=3, help='Scraping depth level (default: 3)')
    parser.add_argument('--threads', type=int, default=5, help='Number of threads (default: 5)')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    print("Multi-Threaded TLD Scraper")
    print("=" * 60)
    print(f"Input file: {args.input}")
    print(f"Scraping level: {args.level}")
    print(f"Threads: {args.threads}")
    print("=" * 60)
    
    # Initialize scraper
    scraper = MultiThreadedTLDScraper(level=args.level, max_workers=args.threads)
    
    try:
        # Read input URLs
        urls_to_scrape = scraper.read_urls_from_file(args.input)
        if not urls_to_scrape:
            print("No valid URLs found to scrape. Exiting.")
            return
        
        print(f"Found {len(urls_to_scrape)} initial URLs to process")
        
        # Perform multi-level scraping with threading
        start_time = time.time()
        scraper.multi_level_scrape(urls_to_scrape)
        end_time = time.time()
        
        # Calculate statistics
        total_time = end_time - start_time
        urls_per_second = scraper.stats['urls_processed'] / total_time if total_time > 0 else 0
        
        # Save results
        if scraper.all_tlds:
            output_filename = os.path.join(
                "url_filter", 
                "categories", 
                "porn", 
                f"threaded_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_hosts.txt"
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
    finally:
        # Always close drivers
        scraper.close()

if __name__ == "__main__":
    main()
