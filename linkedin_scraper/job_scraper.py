import re
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
import logging
from linkedin_scraper.scraper import Scraper


def extract_job_id(url: str) -> int:
    # Regular expression to find the job ID
    match = re.search(r'linkedin.com/jobs/view/(\d+)', url)
    if match:
        try:
            job_id = int(match.group(1))
            return job_id
        except ValueError:
            raise
    else:
        return 0  # Flag for error extracting id


class Job(Scraper):
    # Static variable to store the method for loading job description across instances
    job_description_class = None

    def __init__(
            self,
            linkedin_url=None,
            job_title=None,
            company=None,
            company_linkedin_url=None,
            location=None,
            posted_date=None,
            job_description=None,
            driver=None,
            close_on_complete=True,
            scrape=True,
    ):
        super().__init__()

        # Extract the job ID from the URL, if provided
        self.linkedin_url = linkedin_url
        self.linkedin_job_id = extract_job_id(linkedin_url) if linkedin_url else None

        self.job_title = job_title
        self.driver = driver
        self.company = company
        self.company_linkedin_url = company_linkedin_url
        self.location = location
        self.posted_date = posted_date
        self.job_description = job_description

        if scrape:
            self.check_signed_in_and_scrape_from_linkedin_url(close_on_complete)

    def __repr__(self):
        return f"<Job {self.job_title} {self.company}>"

    def to_dict(self):
        return {
            "linkedin_job_id": self.linkedin_job_id,
            "linkedin_url": self.linkedin_url,
            "job_title": self.job_title,
            "company": self.company,
            "company_linkedin_url": self.company_linkedin_url,
            "location": self.location,
            "posted_date": self.posted_date,
            "job_description": self.job_description,
        }

    def check_signed_in_and_scrape_from_linkedin_url(self, close_on_complete=True):
        if self.is_signed_in():
            self.scrape_data_from_linkedin_url(close_on_complete=close_on_complete)
        else:
            raise RuntimeError("Please log in")

    def scrape_data_from_linkedin_url(self, close_on_complete=True):
        driver = self.driver

        driver.get(self.linkedin_url)
        self.focus()
        self.job_title = self.wait_for_element_to_load(
            name="job-details-jobs-unified-top-card__job-title").find_element(By.TAG_NAME, "h1").text.strip()

        logging.disable(logging.CRITICAL)

        company_element = self.wait_for_element_to_load(name="job-details-jobs-unified-top-card__company-name")
        company_link = company_element.find_elements(By.TAG_NAME, "a")

        if company_link:
            self.company = company_link[0].text.strip()
            self.company_linkedin_url = company_link[0].get_attribute("href")
        else:
            self.company = company_element.text.strip()
            self.company_linkedin_url = None

        logging.disable(logging.NOTSET)

        description_container = self.wait_for_element_to_load(
            name="job-details-jobs-unified-top-card__primary-description-container"
        )
        self.location = description_container.find_element(By.XPATH, ".//div[1]/span[1]").text.strip()

        date_container = description_container.find_element(By.XPATH, ".//div[1]/span[3]")
        spans = date_container.find_elements(By.XPATH, "./span")

        if len(spans) == 2:
            self.posted_date = spans[1].text.strip()
        elif len(spans) == 1:
            self.posted_date = spans[0].text.strip()
        else:
            strong_span = date_container.find_element(By.XPATH, "./strong/span")
            self.posted_date = strong_span.text.strip()

        selenium_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
        previous_log_level = selenium_logger.getEffectiveLevel()
        selenium_logger.setLevel(logging.ERROR)

        if Job.job_description_class is None:
            try:
                job_description_elem = self.wait_for_element_to_load(name="jobs-description")
                self.mouse_click(job_description_elem.find_element(By.TAG_NAME, "button"))
                job_description_elem.find_element(By.TAG_NAME, "button").click()
                Job.job_description_class = "jobs-description"
                self.job_description = job_description_elem.text.strip()
            except (NoSuchElementException, TimeoutException):
                try:
                    job_description_elem = self.wait_for_element_to_load(name="feed-shared-inline-show-more-text")
                    show_more_button = job_description_elem.find_element(By.TAG_NAME, "button")
                    self.mouse_click(show_more_button)
                    show_more_button.click()
                    Job.job_description_class = "feed-shared-inline-show-more-text"
                    self.job_description = job_description_elem.text.strip()
                except (NoSuchElementException, TimeoutException):
                    self.job_description = ""
        else:
            job_description_elem = self.wait_for_element_to_load(name=Job.job_description_class)
            self.mouse_click(job_description_elem.find_element(By.TAG_NAME, "button"))
            job_description_elem.find_element(By.TAG_NAME, "button").click()
            self.job_description = job_description_elem.text.strip()

        if Job.job_description_class == "feed-shared-inline-show-more-text":
            try:
                extra_requirements = self.wait_for_element_to_load(name="job-details-about-the-job-module__section")
                self.job_description += " ||| " + extra_requirements.text.strip()
            except:
                pass

        selenium_logger.setLevel(previous_log_level)

        if close_on_complete:
            driver.close()
