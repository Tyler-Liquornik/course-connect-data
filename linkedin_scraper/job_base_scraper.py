import logging
import os
import sys
from typing import List
from time import sleep
import urllib.parse
import pandas as pd
from linkedin_scraper.scraper import Scraper
from linkedin_scraper.job_scraper import Job
from selenium.webdriver.common.by import By

class JobBase(Scraper):

    AREAS = ["recommended_jobs", None, "still_hiring", "more_jobs"]

    def __init__(self, driver, base_url="https://www.linkedin.com/jobs/", close_on_complete=False, scrape=True,
                 scrape_recommended_jobs=True, csv_filename="linkedin_jobs.csv"):
        super().__init__()
        self.driver = driver
        self.base_url = base_url
        self.csv_filename = csv_filename

        self.create_or_reset_csv()

        if scrape:
            self.scrape(scrape_recommended_jobs)

    def create_or_reset_csv(self):
        # Repeatedly prompt the user to close the CSV file in excel (it can't be open to add the data to it)
        while True:
            try:
                if os.path.exists(self.csv_filename):
                    os.remove(self.csv_filename)
                pd.DataFrame(
                    columns=["linkedin_job_id", "linkedin_url", "job_title", "company", "company_linkedin_url", "location", "posted_date",
                             "job_description", "search_query", "search_date"]).to_csv(self.csv_filename, index=False)
                logging.info("CSV file created or reset successfully.")
                break
            except PermissionError:
                input("Please close " + self.csv_filename + " (probably in Excel) and press Enter to retry...")

    def scrape(self, scrape_recommended_jobs=True):
        if self.is_signed_in():
            self.scrape_logged_in(scrape_recommended_jobs=scrape_recommended_jobs)
        else:
            raise NotImplementedError("This part is not implemented yet")

    # Return a job object with only the linkedin_url not null
    def scrape_linkedin_url(self, base_element) -> Job:
        job_div = self.wait_for_element_to_load(name="job-card-list__title", base=base_element)
        linkedin_url = job_div.get_attribute("href")
        return Job(linkedin_url=linkedin_url, scrape=False, driver=self.driver)

    def scrape_logged_in(self, scrape_recommended_jobs=True):
        driver = self.driver
        driver.get(self.base_url)
        if scrape_recommended_jobs:
            self.focus()
            sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)
            job_area = self.wait_for_element_to_load(name="scaffold-finite-scroll__content")
            areas = self.wait_for_all_elements_to_load(name="artdeco-card", base=job_area)
            for i, area in enumerate(areas):
                area_name = self.AREAS[i]
                if not area_name:
                    continue
                area_results = []
                for job_posting in area.find_elements_by_class_name("jobs-job-board-list__item"):
                    job = self.scrape_linkedin_url(job_posting)
                    area_results.append(job)
                setattr(self, area_name, area_results)
        return

    # Each Job object has only the LinkedIn url so we can click on it and get job details from there
    def search_jobs_page_for_linkedin_urls(self, search_term: str, click_to_first_page: bool = True) -> List[Job]:
        if click_to_first_page:
            url = os.path.join(self.base_url, "search") + f"?keywords={urllib.parse.quote(search_term)}&refresh=true"
            self.driver.get(url)

        self.scroll_to_bottom()
        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)

        job_listing_class_name = "jobs-search-results-list"
        job_listing = self.wait_for_element_to_load(name=job_listing_class_name)

        self.scroll_class_name_element_to_page_percent(job_listing_class_name, 0.3)
        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)

        self.scroll_class_name_element_to_page_percent(job_listing_class_name, 0.6)
        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)

        self.scroll_class_name_element_to_page_percent(job_listing_class_name, 1)
        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)

        job_results = []
        for job_card in self.wait_for_all_elements_to_load(name="job-card-list", base=job_listing):
            job = self.scrape_linkedin_url(job_card)
            job_results.append(job)
        return job_results

    def search_jobs_pages_for_linkedin_urls(self, search_term: str, max_pages: int = sys.maxsize) -> List[Job]:
        try:
            return self.search_jobs_pages_for_linkedin_urls_with_next_button_pagination(search_term, max_pages)
        except:
            return self.search_jobs_pages_for_linkedin_urls_with_ellipsis_button_pagination(search_term, max_pages)

    def search_jobs_pages_for_linkedin_urls_with_next_button_pagination(self, search_term: str, max_pages: int) -> List[Job]:
        url = os.path.join(self.base_url, "search") + f"?keywords={urllib.parse.quote(search_term)}&refresh=true"
        self.driver.get(url)

        # Check for the next button to trigger an exception right away
        try:
            logging.disable(logging.CRITICAL)
            next_button = self.driver.find_element(By.XPATH, "//button[@aria-label='View next page']")
            logging.disable(logging.NOTSET)
        except Exception as e:
            raise e

        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)
        all_job_results = []
        current_page = 1

        while current_page <= max_pages:
            job_results = self.search_jobs_page_for_linkedin_urls(search_term, False)
            all_job_results.extend(job_results)
            next_button = self.driver.find_element(By.XPATH, "//button[@aria-label='View next page']")
            if next_button:
                next_button.click()
                current_page += 1
                sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)
            else:
                break

        return all_job_results

    def search_jobs_pages_for_linkedin_urls_with_ellipsis_button_pagination(self, search_term: str, max_pages: int) -> \
    List[Job]:
        url = os.path.join(self.base_url, "search") + f"?keywords={urllib.parse.quote(search_term)}&refresh=true"
        self.driver.get(url)
        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)

        all_job_results = []
        current_page = 1

        while current_page <= max_pages:
            # Collect job results on the current page
            job_results = self.search_jobs_page_for_linkedin_urls(search_term, False)
            all_job_results.extend(job_results)

            try:
                # Find the pagination container and locate the selected (current) page button
                pagination_container = self.driver.find_element(By.CLASS_NAME, "jobs-search-results-list__pagination")
                selected_button = pagination_container.find_element(By.XPATH,
                                                                    ".//li[contains(@class, 'active')]/button")

                # Try to find the next sibling of the selected button's parent <li> element
                next_li = selected_button.find_element(By.XPATH, "../following-sibling::li/button")

                if next_li and current_page < max_pages:
                    next_li.click()
                    current_page += 1
                    sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)
                else:
                    break
            except Exception:
                break

        return all_job_results
