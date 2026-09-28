import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

def extract_vehicle_data(ad_soup, url):
    vehicle = {
        "Brand": "N/A", "Model": "N/A", "Manufacture Year": "N/A",
        "Engine Capacity": "N/A", "Transmission": "N/A", "Fuel Type": "N/A",
        "Condition": "N/A", "Mileage": "N/A", "Asking Price": "N/A",
        "Publication Date": "N/A", "URL": url
    }

    # 1. Extract Price using regex on all text (matches 'Rs X,XXX,XXX')
    full_text = ad_soup.get_text(separator=" ")
    price_match = re.search(r'Rs\s*[\d,]+', full_text)
    if price_match:
        vehicle["Asking Price"] = price_match.group(0)

    # 2. Extract Publication Date
    date_match = re.search(r'Posted on(.*?),', full_text)
    if date_match:
         vehicle["Publication Date"] = date_match.group(1).strip()

    # 3. Extract specs using a sequential text scan.
    # This ignores HTML classes completely and looks at the actual text on the screen.
    key_map = {
        "Brand": "Brand", "Brand:": "Brand",
        "Model": "Model", "Model:": "Model",
        "Year of Manufacture": "Manufacture Year", "Year of Manufacture:": "Manufacture Year",
        "Engine capacity": "Engine Capacity", "Engine capacity:": "Engine Capacity",
        "Transmission": "Transmission", "Transmission:": "Transmission",
        "Fuel type": "Fuel Type", "Fuel type:": "Fuel Type",
        "Condition": "Condition", "Condition:": "Condition",
        "Mileage": "Mileage", "Mileage:": "Mileage"
    }

    # Get all visible text snippets in the order they appear on the page
    texts = list(ad_soup.stripped_strings)

    for i, text in enumerate(texts):
        if text in key_map:
            field_name = key_map[text]
            # Only assign if we haven't found it yet
            if vehicle[field_name] == "N/A":
                # The actual value is almost always the very next text snippet in the DOM
                if i + 1 < len(texts):
                    value = texts[i + 1]
                    # Ensure the value isn't just another label by accident
                    if value not in key_map:
                        vehicle[field_name] = value

    return vehicle

def scrape_ikman_vehicles(num_pages=1):
    base_url = "https://ikman.lk"
    search_url = f"{base_url}/en/ads/sri-lanka/cars"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    vehicle_data = []

    for page in range(51, num_pages + 1):
        print(f"Fetching search page {page}...")
        try:
            response = requests.get(f"{search_url}?page={page}", headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            ad_links = []
            for a_tag in soup.find_all("a", href=True):
                if "/en/ad/" in a_tag["href"]:
                    full_url = base_url + a_tag["href"] if not a_tag["href"].startswith("http") else a_tag["href"]
                    if full_url not in ad_links:
                        ad_links.append(full_url)

            print(f"Found {len(ad_links)} ads on page {page}. Extracting data...")

            for link in ad_links:
                try:
                    ad_res = requests.get(link, headers=headers)
                    ad_soup = BeautifulSoup(ad_res.text, "html.parser")

                    vehicle = extract_vehicle_data(ad_soup, link)

                    if vehicle["Brand"] != "N/A" or vehicle["Asking Price"] != "N/A":
                        vehicle_data.append(vehicle)
                    else:
                        print(f"Skipping {link} - structure could not be parsed.")

                    time.sleep(1) # Be polite to the server
                except Exception as e:
                    print(f"Failed to extract data from {link}: {e}")

        except Exception as e:
            print(f"Failed to fetch search page {page}: {e}")

    if vehicle_data:
        df = pd.DataFrame(vehicle_data)
        df.to_csv("ikman_vehicle_data_1.csv", index=False)
        print(f"\nScraping complete! {len(vehicle_data)} vehicles saved to 'ikman_vehicle_data.csv'")
    else:
        print("\nNo data was extracted.")

if __name__ == "__main__":
    scrape_ikman_vehicles(num_pages=100)
