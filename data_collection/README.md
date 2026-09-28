# Data collection and cleaning

The three `ikman_vehicle_data*.csv` files are untouched scraped inputs. `cleaned_new_data.csv` contains accepted cleaned listings. `clean_data.py` and `01_merge_and_clean_scraped_data.ipynb` perform the same cleaning process; the notebook is for manual use.

Run from AutoValue: `.venv/bin/python data_collection/clean_data.py`.
The cleaner reads `data/raw/car_price_dataset.csv` to standardize names. It regenerates `merged_raw.csv`, the cleaned CSV, and detailed cleaning-audit files when explicitly run. The app does not execute cleaning or scraping.

`ikman_scraper.py` is the original collection script. Running it performs network requests and writes its output relative to the current working directory; inspect its page range and output filename before reuse.
