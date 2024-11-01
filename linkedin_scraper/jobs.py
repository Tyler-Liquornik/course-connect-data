from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
import logging
from linkedin_scraper.objects import Scraper


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
        self.linkedin_url = linkedin_url
        self.job_title = job_title
        self.driver = driver
        self.company = company
        self.company_linkedin_url = company_linkedin_url
        self.location = location
        self.posted_date = posted_date
        self.job_description = job_description

        if scrape:
            self.scrape(close_on_complete)

    def __repr__(self):
        return f"<Job {self.job_title} {self.company}>"

    def scrape(self, close_on_complete=True):
        if self.is_signed_in():
            self.scrape_logged_in(close_on_complete=close_on_complete)
        else:
            raise RuntimeError("Please log in")

    def to_dict(self):
        return {
            "linkedin_url": self.linkedin_url,
            "job_title": self.job_title,
            "company": self.company,
            "company_linkedin_url": self.company_linkedin_url,
            "location": self.location,
            "posted_date": self.posted_date,
            "job_description": self.job_description,
        }

    def scrape_logged_in(self, close_on_complete=True):
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

        # Locate the container and check for any direct text content within .//div[1]/span[3]
        date_container = description_container.find_element(By.XPATH, ".//div[1]/span[3]")
        spans = date_container.find_elements(By.XPATH, "./span")

        # Reposted case: if text is present and there are two spans, use the second span
        if len(spans) == 2:
            self.posted_date = spans[1].text.strip()
        # Regular case: if only one span, use that one
        elif len(spans) == 1:
            self.posted_date = spans[0].text.strip()
        # Recently posted case (bolded): if no spans, locate strong > span
        else:
            strong_span = date_container.find_element(By.XPATH, "./strong/span")
            self.posted_date = strong_span.text.strip()

        # Suppress Selenium logs temporarily
        selenium_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
        previous_log_level = selenium_logger.getEffectiveLevel()
        selenium_logger.setLevel(logging.ERROR)

        # Attempt to load the job description using the stored method or determine it if unset
        if Job.job_description_class is None:
            try:
                # Try the first method
                job_description_elem = self.wait_for_element_to_load(name="jobs-description")
                self.mouse_click(job_description_elem.find_element(By.TAG_NAME, "button"))
                job_description_elem.find_element(By.TAG_NAME, "button").click()
                Job.job_description_class = "jobs-description"  # Store the successful method
                self.job_description = job_description_elem.text.strip()
            except (NoSuchElementException, TimeoutException):
                try:
                    # Try the alternative method
                    job_description_elem = self.wait_for_element_to_load(name="feed-shared-inline-show-more-text__see-more-less-toggle")
                    self.mouse_click(job_description_elem.find_element(By.TAG_NAME, "button"))
                    job_description_elem.find_element(By.TAG_NAME, "button").click()
                    Job.job_description_class = "feed-shared-inline-show-more-text__see-more-less-toggle"  # Store the successful method
                    self.job_description = job_description_elem.text.strip()
                except (NoSuchElementException, TimeoutException):
                    # Only log this if both methods fail to avoid 404 spam
                    logging.info("No 'See more' button found for job description expansion.")
                    self.job_description = ""
        else:
            # Use the stored method directly
            job_description_elem = self.wait_for_element_to_load(name=Job.job_description_class)
            self.mouse_click(job_description_elem.find_element(By.TAG_NAME, "button"))
            job_description_elem.find_element(By.TAG_NAME, "button").click()
            self.job_description = job_description_elem.text.strip()

        # Restore previous logging level
        selenium_logger.setLevel(previous_log_level)

        if close_on_complete:
            driver.close()