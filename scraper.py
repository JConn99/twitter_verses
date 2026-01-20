import requests
from bs4 import BeautifulSoup
import csv
import time
import re

def scrape_bible_verses():
    """Scrape top 1000 Bible verses from topverses.com and save to CSV"""
    
    verses = []
    base_url = "https://www.topverses.com/Bible/&pg={}&a=ajax"
    
    # Pages 1-100 should give us 1000 verses (10 per page)
    for page in range(1, 101):
        url = base_url.format(page)
        
        print(f"Scraping page {page}/100...")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all verse headers (they're h2 tags with links)
            verse_headers = soup.find_all('h2')
            
            for header in verse_headers:
                try:
                    # Get the reference from the link
                    link = header.find('a')
                    if not link:
                        continue
                    
                    reference = link.text.strip()
                    
                    # Find the verse text container
                    next_elem = header.find_next_sibling()
                    
                    # Skip the "Bible Rank: X" element
                    while next_elem and 'Bible Rank' in next_elem.text:
                        next_elem = next_elem.find_next_sibling()
                    
                    # Get the full text and extract only NIV portion
                    if next_elem:
                        full_text = next_elem.get_text()
                        
                        # Split by translation markers and get the first part (before NIV marker)
                        # The NIV text comes first, before the "NIV" label
                        lines = full_text.split('\n')
                        niv_text = []
                        
                        for line in lines:
                            line = line.strip()
                            # Stop when we hit the NIV marker (that's the end of NIV text)
                            if line == 'NIV' or line == 'AMP' or line == 'KJV':
                                break
                            if line:  # Only add non-empty lines
                                niv_text.append(line)
                        
                        verse_text = ' '.join(niv_text).strip()
                        
                        if verse_text and reference:
                            verses.append({
                                'reference': reference,
                                'text': verse_text
                            })
                            
                            print(f"  Added: {reference}")
                            #print(f"    Text: {verse_text[:60]}...")
                    
                except Exception as e:
                    print(f"  Error parsing verse: {e}")
                    continue
            
            # Be respectful with scraping - add delay between requests
            time.sleep(0.5)
            
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            continue
    
    # Save to CSV
    print(f"\nSaving {len(verses)} verses to bible_verses.csv...")
    with open('bible_verses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['reference', 'text'])
        writer.writeheader()
        writer.writerows(verses)
    
    print("Done!")
    return len(verses)

if __name__ == "__main__":
    count = scrape_bible_verses()
    print(f"\nSuccessfully scraped {count} Bible verses (NIV only)")
    print("Saved to: bible_verses.csv")