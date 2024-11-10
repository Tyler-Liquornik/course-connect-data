import yaml
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from datetime import datetime
import os

from linkedin_scraper.document.course_document import CourseDocument
from linkedin_scraper.scraper.course_scraper import CourseScraper
from mongo_client import get_database
from linkedin_scraper.scraper.job_scraper import JobScraper
from linkedin_scraper.scraper.job_url_scraper import JobUrlScraper
from linkedin_scraper.scraper.subject_scraper import SubjectScraper

def configure_logging(config):
    if config.get("logging", {}).get("enabled", False):
        logging_level = config["logging"].get("level", "INFO").upper()
        logging.basicConfig(level=getattr(logging, logging_level))
    else:
        logging.disable(logging.CRITICAL)

def setup_csv(filename, headers):
    if os.path.isfile(filename):
        os.remove(filename)
        logging.info(f"Deleted existing file: {filename}")
    pd.DataFrame(columns=headers).to_csv(filename, encoding="utf-8", index=False)

def run_job_scraper(config):
    logging.info("Starting Job Scraper")

    # MongoDB setup
    job_ids = []
    if config["save_data_to"] == "MONGO":
        db = get_database()
        jobs_collection = db["jobs"]

    # CSV setup
    csv_filename = "linkedin_jobs.csv"
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
    ]
    setup_csv(csv_filename, headers)

    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()

    # Login to LinkedIn
    driver.get("https://www.linkedin.com/login")
    input("Please manually log in to LinkedIn and press Enter here to continue...")

    # Job search setup
    search_query = input("Enter your job search term: ")
    pages_to_scrape = int(input("Enter the number of pages to scrape (max 40): "))

    job_search = JobUrlScraper(driver=driver, close_on_complete=False, scrape=False)
    job_listings = job_search.search_jobs_pages_for_linkedin_urls(search_query, pages_to_scrape)

    for idx, job_listing in enumerate(job_listings):
        try:
            logging.info(f"Processing job {idx+1}/{len(job_listings)}: {job_listing.linkedin_url}")
            job = JobScraper(job_listing.linkedin_url, driver=driver, scrape=True, close_on_complete=False)
            job_data = job.to_dict()
            job_data["search_query"] = search_query
            job_data["search_date"] = datetime.today().strftime("%Y-%m-%d")
            logging.debug(job_data)

            # Save each job to MongoDB or CSV
            if config["save_data_to"] == "MONGO":
                result = jobs_collection.insert_one(job_data)
                job_ids.append(str(result.inserted_id))
                logging.info(f"Saved job {idx+1} to MongoDB")
            elif config["save_data_to"] == "CSV":
                job_df = pd.DataFrame([job_data])
                job_df.to_csv(csv_filename, encoding="utf-8", mode='a', header=False, index=False)
                logging.info(f"Appended job {idx+1} to CSV")

        except Exception as e:
            logging.error(f"Error processing job {idx+1}: {e}")

    driver.quit()
    logging.info("Job scraping complete!")

    # if config["save_data_to"] == "MONGO" and job_ids:
    #     tokenizer = JobProcessor()
    #     tokenizer.process_jobs(job_ids)

def run_course_scraper(config):
    logging.info("Starting Course Scraper")

    # MongoDB setup
    if config["save_data_to"] == "MONGO":
        db = get_database()
        subjects_collection = db["subjects"]
        courses_collection = db["courses"]

    # CSV setup for subjects
    subjects_csv = "subjects.csv"
    subjects_headers = [
        "subject_code",
        "breadth_category",
        "course_list_url",
    ]
    setup_csv(subjects_csv, subjects_headers)

    # CSV setup for courses
    courses_csv = "courses.csv"
    courses_headers = [
        "subject_id",
        "number",
        "suffix",
        "campus",
        "description",
        "course_outline_ids",
    ]
    setup_csv(courses_csv, courses_headers)

    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()

    try:
        # Step 1: Scrape all subjects
        subject_scraper = SubjectScraper(driver=driver)
        subjects = subject_scraper.scrape_all_subjects(driver=driver)
        for idx, subject_data in enumerate(subjects):
            try:
                if config["save_data_to"] == "MONGO":
                    result = subjects_collection.insert_one(subject_data.to_mongo().to_dict())
                    subject_data.id =  result.inserted_id
                    logging.info(f"Saved subject {idx+1}: {subject_data.subject_code}")
                elif config["save_data_to"] == "CSV":
                    subject_df = pd.DataFrame([subject_data.to_mongo().to_dict()])
                    subject_df.to_csv(subjects_csv, encoding="utf-8", mode="a", header=False, index=False)
                    logging.info(f"Appended subject {idx+1}: {subject_data.subject_code} to CSV")
                else:
                    raise RuntimeError("Choose a valid save_data_to value")
            except Exception as e:
                logging.error(f"Error saving subject {idx+1}: {e}")

        # Step 2: Use course_list_url to scrape courses for each subject
        for idx, subject_data in enumerate(subjects):
            try:
                course_scraper = CourseScraper()
                course_list_url = subject_data.course_list_url
                subject_id = subject_data.id
                courses = course_scraper.scrape_all_courses(driver=driver, url=course_list_url, subject_id=subject_id)
                for course_document in courses:
                    course_data_dict = course_document.to_mongo().to_dict()
                    if config["save_data_to"] == "MONGO":
                        courses_collection.insert_one(course_data_dict)
                    elif config["save_data_to"] == "CSV":
                        course_df = pd.DataFrame([course_data_dict])
                        course_df.to_csv("courses.csv", mode="a", header=False, index=False)
            except Exception as e:
             logging.error(f"Error scraping courses for subject {subject_data.subject_code}: {e}")

    finally:
        driver.quit()
        logging.info("Course scraping complete!")


        # if config["save_data_to"] == "MONGO" and course_ids:
        #     processor = CoursesProcessor()
        #     processor.process_courses(course_ids)



if __name__ == "__main__":
    # Load configuration
    with open("config.yaml") as file:
        config = yaml.safe_load(file)

    # Configure logging
    configure_logging(config)

    # Prompt user to choose scraper
    print("Select a scraper to run:")
    print("1. Job Scraper")
    print("2. Course Scraper")
    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == "1":
        run_job_scraper(config)
    elif choice == "2":
        run_course_scraper(config)
    else:
        print("Invalid choice. Exiting.")
