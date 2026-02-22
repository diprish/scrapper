import requests
import json
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/"
TOC_URL = urljoin(BASE_URL, "toc.js")

def get_soup(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_toc_links():
    print(f"Fetching TOC: {TOC_URL}")
    try:
        response = requests.get(TOC_URL)
        response.raise_for_status()
        content = response.text
        
        # Strip 'define(' and ')' to parse as JSON
        # Content format: define({...});
        match = re.search(r'define\s*\((.*)\);?', content, re.DOTALL)
        if not match:
            print("Could not parse TOC JS structure")
            return []
            
        json_str = match.group(1)
        data = json.loads(json_str)
        
        links = []
        
        def traverse(node):
            if 'href' in node and 'title' in node:
                href = node['href']
                # Filter out non-content pages
                if href and not href.startswith('index.html') and not href.startswith('get-help') and not href.startswith('http'):
                    # Remove anchor fragment
                    clean_href = href.split('#')[0]
                    full_url = urljoin(BASE_URL, clean_href)
                    
                    # Only add if not already present (though TOC usually unique)
                    links.append({
                        "url": full_url,
                        "title": node['title']
                    })
            
            if 'topics' in node:
                for child in node['topics']:
                    traverse(child)
                    
        if 'toc' in data:
            for item in data['toc']:
                traverse(item)
                
        return links
        
    except Exception as e:
        print(f"Error fetching TOC: {e}")
        return []

def scrape_oracle_docs():
    links = get_toc_links()
    print(f"Found {len(links)} potential tables/views from TOC.")
    
    if not links:
        print("No links found! Check your connection or the TOC URL.")
        return

    print("Opening oracle_financials_26a.json for writing...")
    with open('oracle_financials_26a.json', 'w', encoding='utf-8') as f:
        f.write('[\n')
        first_entry = True
        
        for i, item in enumerate(links):
            url = item['url']
            name = item['title']
            
            print(f"Processing {i+1}/{len(links)}: {name}")
            
            soup = get_soup(url)
            if not soup:
                print(f"  -> Failed to fetch page")
                continue
                
            try:
                # Description
                description = ""
                main_content = soup.find('article') or soup.find('main') or soup.body
                if main_content:
                    # Try specific classes first
                    short_desc = main_content.find(class_='shortdesc')
                    if short_desc:
                        description = short_desc.get_text(strip=True)
                    else:
                        # Fallback to first paragraph
                        p = main_content.find('p')
                        if p:
                            description = p.get_text(strip=True)

                # Columns
                columns = []
                tables = soup.find_all('table')
                target_table = None
                max_score = 0
                
                # Debug: print found tables count
                # print(f"  -> Found {len(tables)} tables on page")

                for t in tables:
                    headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
                    score = 0
                    if 'datatype' in headers or 'data type' in headers or 'type' in headers:
                        score += 10
                    if 'null' in headers or 'not-null' in headers:
                        score += 5
                    if 'precision' in headers or 'length' in headers:
                        score += 5
                    if 'comments' in headers or 'description' in headers:
                        score += 5
                    if 'name' in headers or 'column' in headers:
                        score += 1
                    
                    if score > max_score:
                        max_score = score
                        target_table = t
                
                # Fallback to first table if no clear winner (and score is low)
                if not target_table and tables:
                    target_table = tables[0]
                    
                if target_table:
                    # Extract headers
                    headers = [th.get_text(strip=True) for th in target_table.find_all('th')]
                    if not headers:
                        # Try first row as header
                        first_row = target_table.find('tr')
                        if first_row:
                            headers = [td.get_text(strip=True) for td in first_row.find_all('td')]
                    
                    # Extract rows
                    for row in target_table.find_all('tr'):
                        cols = row.find_all('td')
                        if not cols: continue
                        
                        # Skip if it matches headers
                        first_col_text = cols[0].get_text(strip=True)
                        if headers and first_col_text == headers[0]: continue
                        
                        col_data = {}
                        for j, col in enumerate(cols):
                            if j < len(headers):
                                col_data[headers[j]] = col.get_text(strip=True)
                        
                        if col_data:
                            columns.append(col_data)

                entry = {
                    "name": name,
                    "url": url,
                    "description": description,
                    "columns": columns
                }
                
                if columns:
                    if not first_entry:
                        f.write(',\n')
                    json.dump(entry, f, indent=2)
                    first_entry = False
                    f.flush()
                    print(f"  -> Wrote {len(columns)} columns to file")
                else:
                    print(f"  -> No columns found (skipped writing)")
                    
            except Exception as e:
                print(f"Error parsing {url}: {e}")
                
            # Be nice to the server
            time.sleep(0.2)
            
        f.write('\n]')
        
    print(f"Scraping complete. Data saved to oracle_financials_26a.json")

if __name__ == "__main__":
    scrape_oracle_docs()
