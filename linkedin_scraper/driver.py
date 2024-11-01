import yaml
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from linkedin_scraper.jobs import Job
from linkedin_scraper.job_search import JobSearch
import time

# Load configuration from YAML
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Configure logging
if config.get("logging", {}).get("enabled", False):
    logging_level = config["logging"].get("level", "INFO").upper()
    logging.basicConfig(level=getattr(logging, logging_level))
else:
    logging.disable(logging.CRITICAL)  # Disable all logging if not enabled

logging.info("Scraper Start")

# Initialize the driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
# driver = webdriver.Chrome(service=Service(ChromeDriverManager(driver_version="114.0.5735.90").install()))
driver.maximize_window()

# Open LinkedIn login page
driver.get("https://www.linkedin.com/login")
input("Please manually log in to LinkedIn and press Enter here to continue...")

search_query = "Software Engineer"

# Perform the job search to get incomplete job data
job_search = JobSearch(driver=driver, close_on_complete=False, scrape=False)
job_listings = job_search.search_pages_for_linkedin_urls(search_query, 6)

# Initialize an empty DataFrame with the exact fields from the Job class's to_dict() method
jobs_df = pd.DataFrame(columns=[
    "linkedin_url",
    "job_title",
    "company",
    "company_linkedin_url",
    "location",
    "posted_date",
    "job_description"
])

# Extract details for each job and append directly to the DataFrame
for idx, job_listing in enumerate(job_listings):
    try:
        logging.info(f"Processing job {idx+1}/{len(job_listings)}: {job_listing.linkedin_url}")

        # Initialization of the job object with the LinkedIn url will scrape out all the details for it
        job = Job(job_listing.linkedin_url, driver=driver, scrape=True, close_on_complete=False)

        # Use the to_dict() method to get job data
        job_data = job.to_dict()
        logging.info(job_data)

        # Append the job_data to the DataFrame
        jobs_df = pd.concat([jobs_df, pd.DataFrame([job_data])], ignore_index=True)

        # Optional: Log the scraped data for verification
        logging.info(f"Scraped data for job {idx+1}: {job_data}")

    except Exception as e:
        logging.error(f"Error processing job {idx+1}: {e}")

# Save to a CSV file
csv_filename = "linkedin_jobs.csv"
jobs_df.to_csv(csv_filename, index=False)

# Close the browser when done
driver.quit()
logging.info(f"Scraping complete! Job data saved to {csv_filename}")