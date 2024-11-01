import logging
import os
import sys
from typing import List
from time import sleep, time
import urllib.parse
import pandas as pd
from linkedin_scraper.objects import Scraper
from linkedin_scraper.jobs import Job
from selenium.webdriver.common.by import By


class JobSearch(Scraper):
    """
    A class to search and scrape job listings from LinkedIn.

    Attributes:
        AREAS (List[str]): Categories to scrape on the LinkedIn jobs page.
        driver (webdriver): The Selenium WebDriver instance.
        base_url (str): The base URL for LinkedIn job listings.
    """
    AREAS = ["recommended_jobs", None, "still_hiring", "more_jobs"]

    def __init__(self, driver, base_url="https://www.linkedin.com/jobs/", close_on_complete=False, scrape=True,
                 scrape_recommended_jobs=True):
        """
        Initializes the JobSearch class.

        Args:
            driver (webdriver): The Selenium WebDriver instance.
            base_url (str): The base URL for LinkedIn job listings. Defaults to "https://www.linkedin.com/jobs/".
            close_on_complete (bool): Whether to close the driver after scraping. Defaults to False.
            scrape (bool): Whether to start scraping immediately. Defaults to True.
            scrape_recommended_jobs (bool): Whether to scrape recommended jobs specifically. Defaults to True.
        """
        super().__init__()
        self.driver = driver
        self.base_url = base_url

        if scrape:
            self.scrape(close_on_complete, scrape_recommended_jobs)

    def scrape(self, close_on_complete=True, scrape_recommended_jobs=True):
        """
        Initiates the scraping process. Checks if the user is signed in.

        Args:
            close_on_complete (bool): Whether to close the driver after scraping. Defaults to True.
            scrape_recommended_jobs (bool): Whether to scrape recommended jobs. Defaults to True.

        Raises:
            NotImplementedError: If the user is not signed in.
        """
        if self.is_signed_in():
            self.scrape_logged_in(close_on_complete=close_on_complete, scrape_recommended_jobs=scrape_recommended_jobs)
        else:
            raise NotImplementedError("This part is not implemented yet")

    def scrape_job_card(self, base_element) -> Job:
        """
        Scrapes individual job card details from a job listing element.

        Args:
            base_element (WebElement): The WebElement for the job card.

        Returns:
            Job: A Job object with details scraped from the job card.
        """
        job_div = self.wait_for_element_to_load(name="job-card-list__title", base=base_element)
        job_title = job_div.text.strip()
        linkedin_url = job_div.get_attribute("href")
        company = base_element.find_element(By.CLASS_NAME, "artdeco-entity-lockup__subtitle").text
        location = base_element.find_element(By.CLASS_NAME, "job-card-container__metadata-wrapper").text
        job = Job(linkedin_url=linkedin_url, job_title=job_title, company=company, location=location, scrape=False,
                  driver=self.driver)
        return job

    def scrape_logged_in(self, close_on_complete=True, scrape_recommended_jobs=True):
        """
        Scrapes job listings while logged in.

        Args:
            close_on_complete (bool): Whether to close the driver after scraping. Defaults to True.
            scrape_recommended_jobs (bool): Whether to scrape recommended jobs specifically. Defaults to True.
        """
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
                    job = self.scrape_job_card(job_posting)
                    area_results.append(job)
                setattr(self, area_name, area_results)
        return

    def search(self, search_term: str, apply_search: bool = True) -> List[Job]:
        """
        Searches for jobs based on a search term.

        Args:
            search_term (str): The search term or job title to look for.
            apply_search (bool): Whether to perform the search on LinkedIn. Defaults to True.

        Returns:
            List[Job]: A list of Job objects scraped from the search results.
        """
        if apply_search:
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
            job = self.scrape_job_card(job_card)
            job_results.append(job)
        return job_results

    def search_all(self, search_term: str, max_pages: int = sys.maxsize) -> List[Job]:
        """
        Searches for jobs across multiple pages based on a search term.

        Args:
            search_term (str): The search term or job title to look for.
            max_pages (int): The maximum number of pages to scrape. Defaults to sys.maxsize.

        Returns:
            List[Job]: A list of Job objects scraped from all pages.
        """
        try:
            next_button = self.driver.find_element(By.XPATH, "//button[@aria-label='View next page']")
            return self.search_all_with_next_button(search_term, max_pages)
        except:
            return self.search_all_without_next_button(search_term, max_pages)

    def search_all_with_next_button(self, search_term: str, max_pages: int, csv_filename="linkedin_jobs.csv") -> List[
        Job]:
        """
        Searches and scrapes job listings using the "Next" button for pagination, saving results to CSV.

        Args:
            search_term (str): The search term or job title to look for.
            max_pages (int): The maximum number of pages to scrape.
            csv_filename (str): The filename for the CSV output. Defaults to "linkedin_jobs.csv".

        Returns:
            List[Job]: A list of Job objects scraped from all pages.
        """
        url = os.path.join(self.base_url, "search") + f"?keywords={urllib.parse.quote(search_term)}&refresh=true"
        self.driver.get(url)
        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)

        all_job_results = []
        current_page = 1

        # Prepare DataFrame to store jobs temporarily
        jobs_df = pd.DataFrame(
            columns=["linkedin_url", "job_title", "company", "company_linkedin_url", "location", "posted_date",
                     "job_description"])

        while current_page <= max_pages:
            job_results = self.search(search_term, False)
            all_job_results.extend(job_results)

            # For each job on the current page, collect detailed information
            for idx, job_listing in enumerate(job_results):
                try:
                    logging.info(f"Processing job {idx + 1} on page {current_page}: {job_listing.linkedin_url}")
                    job = Job(job_listing.linkedin_url, driver=self.driver, scrape=True, close_on_complete=False)
                    time.sleep(1)  # Be polite to avoid being blocked
                    job_data = job.to_dict()

                    # Append job_data to the DataFrame
                    jobs_df = pd.concat([jobs_df, pd.DataFrame([job_data])], ignore_index=True)
                except Exception as e:
                    logging.error(f"Error processing job {idx + 1} on page {current_page}: {e}")

            # Save the jobs of the current page to the CSV file
            jobs_df.to_csv(csv_filename, mode='a', header=not pd.read_csv(csv_filename).empty, index=False)
            jobs_df = pd.DataFrame()  # Clear DataFrame for the next page

            # Click the "Next" button to go to the next page
            try:
                next_button = self.driver.find_element(By.XPATH, "//button[@aria-label='View next page']")
                next_button.click()
                current_page += 1
                sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)  # Wait for the next page to load
            except Exception as e:
                print("No more pages or pagination error:", e)
                break

        return all_job_results

    def search_all_without_next_button(self, search_term: str, max_pages: int, csv_filename="linkedin_jobs.csv") -> \
    List[Job]:
        """
        Searches and scrapes job listings using numbered pagination buttons, saving results to CSV.

        Args:
            search_term (str): The search term or job title to look for.
            max_pages (int): The maximum number of pages to scrape.
            csv_filename (str): The filename for the CSV output. Defaults to "linkedin_jobs.csv".

        Returns:
            List[Job]: A list of Job objects scraped from all pages.
        """
        url = os.path.join(self.base_url, "search") + f"?keywords={urllib.parse.quote(search_term)}&refresh=true"
        self.driver.get(url)
        self.focus()
        sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)

        all_job_results = []
        current_page = 1

        # Prepare DataFrame to store jobs temporarily
        jobs_df = pd.DataFrame(
            columns=["linkedin_url", "job_title", "company", "company_linkedin_url", "location", "posted_date",
                     "job_description"])

        while current_page <= max_pages:
            job_results = self.search(search_term)
            all_job_results.extend(job_results)

            # For each job on the current page, collect detailed information
            for idx, job_listing in enumerate(job_results):
                try:
                    logging.info(f"Processing job {idx + 1} on page {current_page}: {job_listing.linkedin_url}")
                    job = Job(job_listing.linkedin_url, driver=self.driver, scrape=True, close_on_complete=False)
                    time.sleep(1)  # Be polite to avoid being blocked
                    job_data = job.to_dict()

                    # Append job_data to the DataFrame
                    jobs_df = pd.concat([jobs_df, pd.DataFrame([job_data])], ignore_index=True)
                except Exception as e:
                    logging.error(f"Error processing job {idx + 1} on page {current_page}: {e}")

            # Save the jobs of the current page to the CSV file
            jobs_df.to_csv(csv_filename, mode='a', header=not pd.read_csv(csv_filename).empty, index=False)
            jobs_df = pd.DataFrame()  # Clear DataFrame for the next page

            # Navigate to the next page by clicking the corresponding numbered pagination button
            try:
                pagination_buttons = self.driver.find_elements(By.CLASS_NAME, "jobs-search-pagination__indicator")
                if current_page < len(pagination_buttons):
                    pagination_buttons[current_page].click()
                    current_page += 1
                    sleep(self.WAIT_FOR_ELEMENT_TIMEOUT)  # Wait for the page to load
                else:
                    break
            except Exception as e:
                logging.info(f"No more pages or pagination error: {e}")
                break

        return all_job_results