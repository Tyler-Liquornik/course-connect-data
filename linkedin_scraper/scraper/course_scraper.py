import logging
from typing import List
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from linkedin_scraper.document.course_document import CourseDocument
from linkedin_scraper.document.enums.campus import Campus


def parse_course_title(title: str):
    try:
        parts = title.strip().split(" ")
        number_and_suffix = next(part for part in parts if any(char.isdigit() for char in part))
        number_part = "".join([char for char in number_and_suffix if char.isdigit()])
        suffix_part = number_and_suffix[len(number_part):].strip()
        number = int(number_part)
        return number, suffix_part
    except Exception as e:
        logging.error(f"Failed to parse course title: {title}. Error: {e}")
        return None, None


class CourseScraper:
    @staticmethod
    def scrape_all_courses(driver: WebDriver, url: str, subject_id) -> List[CourseDocument]:
        courses = []
        try:
            driver.get(url)
            course_panels = driver.find_elements(By.XPATH, "//div[@class='col-md-12']")
            course_panels.pop(0)
            for idx, panel in enumerate(course_panels):
                try:
                    course_title_element = panel.find_element(By.XPATH, ".//h4[@class='courseTitleNoBlueLink']/a")
                    course_title = course_title_element.text.strip()
                    number, suffix = parse_course_title(course_title)

                    description_element = panel.find_element(By.XPATH, ".//div[@class='panel-body']/div/div")
                    description = description_element.text.strip()

                    campus_image_element = panel.find_element(By.XPATH, ".//img[contains(@class, 'pull-right')]")
                    campus_image_alt = campus_image_element.get_attribute("alt")

                    if "Western Main Campus" in campus_image_alt:
                        campus = Campus.WESTERN.value
                    elif "King's" in campus_image_alt:
                        campus = Campus.KINGS.value
                    elif "Huron" in campus_image_alt:
                        campus = Campus.HURON.value
                    else:
                        campus = None

                    course_document = CourseDocument(
                        subject_id=subject_id,
                        number=number,
                        suffix=suffix,
                        description=description,
                        campus=campus,
                        course_outline_ids=[],
                    )
                    courses.append(course_document)

                    logging.info(f"Scraped course: {course_title}")

                except NoSuchElementException as e:
                    logging.error(f"Error processing course panel: {e}")
        except Exception as e:
            logging.error(f"Error scraping courses from {url}: {e}")
        return courses
