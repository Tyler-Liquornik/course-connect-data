from mongoengine import StringField, ListField
from linkedin_scraper.document.base_document import BaseDocument
from linkedin_scraper.document.enums.school import School
from linkedin_scraper.document.enums.breadth_category import BreadthCategory

class Subject(BaseDocument):
    meta = {'collection': 'subjects'}

    schools = ListField(StringField(choices=[s.value for s in School]))
    breadth_category = StringField(choices=[c.value for c in BreadthCategory])
    subject_code = StringField()