import yaml
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from linkedin_scraper.job_scraper import Job
from linkedin_scraper.job_base_scraper import JobBase
from datetime import datetime
import os
from mongo_client import get_database
from job_processor import JobProcessor
from bson import ObjectId

# Load configuration from YAML
with open("config.yaml") as file:
    config = yaml.safe_load(file)

# Configure logging
if config.get("logging", {}).get("enabled", False):
    logging_level = config["logging"].get("level", "INFO").upper()
    logging.basicConfig(level=getattr(logging, logging_level))
else:
    logging.disable(logging.CRITICAL)

logging.info("Scraper Start")

# Set up MongoDB collection only if 'save_data_to' is set to 'MONGO'
job_ids = []
if config["save_data_to"] == "MONGO":
    db = get_database()
    jobs_collection = db["jobs"]

# CSV and Pandas DataFrame setup
csv_filename = "linkedin_jobs.csv"
if os.path.isfile(csv_filename):
    os.remove(csv_filename)
    logging.info(f"Deleted existing file: {csv_filename}")

# Define the CSV header by setting up a DataFrame with column names, and write the header to the new CSV file
headers = [
    "linkedin_job_id",
    "linkedin_url",
    "job_title",
    "company",
    "company_linkedin_url",
    "location",
    "posted_date",
    "job_description",
    "search_query",
    "search_date"
]
pd.DataFrame(columns=headers).to_csv(csv_filename, encoding="utf-8", index=False)

# Initialize the driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.maximize_window()

# Open LinkedIn login page
driver.get("https://www.linkedin.com/login")
input("Please manually log in to LinkedIn and press Enter here to continue...")

search_query = input("Enter your job search term: ")
pages_to_scrape = 1  # LinkedIn only generates up to 40 pages, >40 acts as 40 pages

job_search = JobBase(driver=driver, close_on_complete=False, scrape=False)
job_listings = job_search.search_jobs_pages_for_linkedin_urls(search_query, pages_to_scrape)

for idx, job_listing in enumerate(job_listings):
    try:
        logging.info(f"Processing job {idx+1}/{len(job_listings)}: {job_listing.linkedin_url}")
        job = Job(job_listing.linkedin_url, driver=driver, scrape=True, close_on_complete=False)
        job_data = job.to_dict()
        job_data["search_query"] = search_query
        job_data["search_date"] = datetime.today().strftime("%Y-%m-%d")
        logging.debug(job_data)

        # Save each job directly to MongoDB or CSV based on configuration
        if config["save_data_to"] == "MONGO":
            result = jobs_collection.insert_one(job_data)
            job_ids.append(str(result.inserted_id))  # Collect the _id of the inserted job
            logging.info(f"Saved job {idx+1} to MongoDB: {job_data}")
        elif config["save_data_to"] == "CSV":
            # Convert job_data to a DataFrame and append to the CSV file
            job_df = pd.DataFrame([job_data])
            job_df.to_csv(csv_filename, encoding="utf-8", mode='a', header=False, index=False)
            logging.info(f"Appended job {idx+1} to CSV")

    except Exception as e:
        logging.error(f"Error processing job {idx+1}: {e}")

# Close the browser when done
driver.quit()
logging.info("Scraping complete!")

# Instantiate and run the tokenizer on specific jobs after scraping
if config["save_data_to"] == "MONGO" and job_ids:
    tokenizer = JobProcessor()  # Instantiate the JobTokenizer class
    tokenizer.process_jobs(job_ids)  # Pass the list of inserted job IDs for processing
