from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from linkedin_scraper.jobs import Job
from linkedin_scraper.job_search import JobSearch
import time

print("Scraper Start")

# Initialize the driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.maximize_window()

# Open LinkedIn login page
driver.get("https://www.linkedin.com/login")
input("Please manually log in to LinkedIn and press Enter here to continue...")

search_query = "Software Engineer"

# Perform the job search
job_search = JobSearch(driver=driver, close_on_complete=False, scrape=False)
job_listings = job_search.search(search_query)

# Initialize an empty DataFrame with the exact fields from the Job class's to_dict() method
jobs_df = pd.DataFrame(columns=[
    "linkedin_url",
    "job_title",
    "company",
    "company_linkedin_url",
    "location",
    "posted_date",
    "applicant_count",
    "job_description",
    "benefits"
])

# Extract details for each job and append directly to the DataFrame
for idx, job_listing in enumerate(job_listings):
    try:
        print(f"Processing job {idx+1}/{len(job_listings)}: {job_listing.linkedin_url}")
        # Create a Job object for each job listing to scrape all the details
        job = Job(job_listing.linkedin_url, driver=driver, scrape=True, close_on_complete=False)
        time.sleep(1)  # Be polite and avoid being blocked

        # Use the to_dict() method to get job data
        job_data = job.to_dict()

        # Append the job_data to the DataFrame
        jobs_df = jobs_df.append(job_data, ignore_index=True)

        # Optional: Print the scraped data for verification
        print(f"Scraped data for job {idx+1}: {job_data}")

    except Exception as e:
        print(f"Error processing job {idx+1}: {e}")

# Save to a CSV file
csv_filename = "linkedin_software_engineer_jobs.csv"
jobs_df.to_csv(csv_filename, index=False)

# Close the browser when done
driver.quit()
print(f"Scraping complete! Job data saved to {csv_filename}")
