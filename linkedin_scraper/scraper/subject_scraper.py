import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from linkedin_scraper.document.enums.breadth_category import BreadthCategory
from linkedin_scraper.document.subject_document import SubjectDocument
from linkedin_scraper.scraper.base_scraper import BaseScraper


class SubjectScraper(BaseScraper):
    URL = "https://www.westerncalendar.uwo.ca/Courses.cfm?SelectedCalendar=Live"

    def __init__(self, driver: WebDriver):
        super().__init__(driver=driver)
        self.url = None

    def __repr__(self):
        return f"<SubjectScraper url={self.url}>"

    @staticmethod
    def scrape_all_subjects(driver: WebDriver):
        """Scrapes all subjects and their associated course URLs."""
        subjects = []
        try:
            driver.get(SubjectScraper.URL)
            subject_rows = driver.find_elements(By.XPATH, "//table[@id='DataTables_Table_0']/tbody/tr")
            for row in subject_rows:
                try:
                    # Extract subject details from the row
                    link_element = row.find_element(By.XPATH, "./td[1]/a")
                    link = link_element.get_attribute("href")
                    subject_code = link.split("Subject=")[1].split("&")[0]
                    subject_name = link_element.text.strip()

                    # Parse breadth categories (can be one or multiple)
                    breadth_category_element = row.find_element(By.XPATH, "./td[2]")
                    raw_categories = breadth_category_element.text.strip().split(" ")
                    breadth_categories = []
                    for category in raw_categories:
                        if category == "A":
                            breadth_categories.append(BreadthCategory.A)
                        elif category == "B":
                            breadth_categories.append(BreadthCategory.B)
                        elif category == "C":
                            breadth_categories.append(BreadthCategory.C)

                    # Convert to structured SubjectDocument
                    subject_document = SubjectDocument(
                        subject_name=subject_name,
                        subject_code=subject_code,
                        course_list_url = link,
                        breadth_categories=[c.value for c in breadth_categories],
                    )
                    subjects.append(subject_document)

                except Exception as e:
                    logging.error(f"Error processing row: {e}")
        except Exception as e:
            logging.error(f"Error scraping all subjects: {e}")
        return subjects