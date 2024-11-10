from mongoengine import StringField, ListField
from linkedin_scraper.document.base_document import BaseDocument
from linkedin_scraper.document.enums.breadth_category import BreadthCategory


class SubjectDocument(BaseDocument):
    meta = {'collection': 'subjects'}

    breadth_categories = ListField(StringField(choices=[c.value for c in BreadthCategory]))  # Updated to ListField
    subject_code = StringField()
    subject_name = StringField()
    course_list_url = StringField()
