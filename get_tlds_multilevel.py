#!/usr/bin/env python3
"""
Multi-Level TLD Scraper using System ChromeDriver
Usage: python3 get_tlds_multilevel.py --input source.txt --level 3

# Option 1: Let it auto-detect ChromeDriver
python3 get_tlds_multilevel.py --input sources/listers_urls.txt --level 3

# Option 2: Explicitly specify ChromeDriver path
python3 get_tlds_multilevel.py --input sources/listers_urls.txt --level 3 --chromedriver-path /usr/local/bin/chromedriver

# Option 3: If chromedriver is in a different location, find it first:
which chromedriver
# Then use that path with --chromedriver-path

"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
import tldextract
import datetime
import time
import argparse
import sys
import os
from collections import deque
import subprocess

class MultiLevelTLDScraper:
    def __init__(self, level=3):
        self.level = level
        self.all_tlds = set()
        self.visited_urls = set()
        self.stats = {
            'urls_processed': 0,
            'urls_found': 0,
            'errors': 0
        }
        self.driver = None
        
    def find_chromedriver(self):
        """Find ChromeDriver in common locations"""
        possible_paths = [
            "/usr/local/bin/chromedriver",  # Common install location
            "/usr/bin/chromedriver",        # System bin
            "/snap/bin/chromedriver",       # Snap installation
            os.path.expanduser("~/.local/bin/chromedriver"),  # User local
            "chromedriver",  # In PATH
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                print(f"✓ Found ChromeDriver at: {path}")
                return path
                
        # Try to find via which command
        try:
            result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                print(f"✓ Found ChromeDriver via which: {path}")
                return path
        except:
            pass
            
        print("✗ ChromeDriver not found in common locations")
        return None

    def setup_driver(self):
        """Setup and configure Chrome driver using system ChromeDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Find ChromeDriver path
        chromedriver_path = self.find_chromedriver()
        
        if not chromedriver_path:
            print("✗ ChromeDriver not found. Please install it or add to PATH.")
            print("Download from: https://chromedriver.chromium.org/")
            return None
        
        try:
            service = Service(executable_path=chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            print("✓ ChromeDriver setup successful")
            return driver
        except Exception as e:
            print(f"✗ Error setting up Chrome driver: {e}")
            print(f"ChromeDriver path used: {chromedriver_path}")
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
        """Scrape all URLs from a given website"""
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
            self.stats['errors'] += 1
        except WebDriverException as e:
            print(f"  Error accessing {url}: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            print(f"  Unexpected error with {url}: {e}")
            self.stats['errors'] += 1
        
        return found_urls

    def multi_level_scrape(self, start_urls):
        """Perform multi-level scraping"""
        if not self.get_driver():
            print("Cannot start scraping - driver not available")
            return
            
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
            
            # Update stats
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
                        self.all_tlds.add(tld)
                    
                    # Add to queue for next level if not at max level
                    if current_level + 1 < self.level:
                        queue.append((url, current_level + 1))
                        new_urls_count += 1
            
            # Update found URLs count
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

    def save_tlds_to_file(self, filename, input_file):
        """Save TLDs to a text file in Linux hosts format"""
        try:
            # Ensure the directory exists
            self.ensure_directory_exists(filename)
            
            with open(filename, 'w', encoding='utf-8') as file:
                # Write header information
                file.write("# Linux hosts file generated by Multi-Level TLD Scraper\n")
                file.write(f"# Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write(f"# Input file: {input_file}\n")
                file.write(f"# URLs processed: {self.stats['urls_processed']}\n")
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
                print("Chrome driver closed")
            except:
                pass

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Multi-level TLD scraper using Selenium')
    parser.add_argument('--input', required=True, help='Input file containing URLs (one per line)')
    parser.add_argument('--level', type=int, default=3, help='Scraping depth level (default: 3)')
    parser.add_argument('--chromedriver-path', help='Explicit path to ChromeDriver (optional)')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    print("Multi-Level TLD Scraper")
    print("=" * 60)
    print(f"Input file: {args.input}")
    print(f"Scraping level: {args.level}")
    if args.chromedriver_path:
        print(f"ChromeDriver path: {args.chromedriver_path}")
    print("=" * 60)
    
    # Initialize scraper
    scraper = MultiLevelTLDScraper(level=args.level)
    
    # Override ChromeDriver path if provided
    if args.chromedriver_path:
        scraper.find_chromedriver = lambda: args.chromedriver_path
    
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
                "url_filter", 
                "categories", 
                "porn", 
                f"multilevel_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_hosts.txt"
            )
            
            if scraper.save_tlds_to_file(output_filename, args.input):
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
