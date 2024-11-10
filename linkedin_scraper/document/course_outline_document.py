from mongoengine import StringField, IntField
from linkedin_scraper.document.base_document import BaseDocument
from linkedin_scraper.document.enums.campus import Campus

class CourseOutlineDocument(BaseDocument):
    meta = {'collection': 'course_outlines'}

    code = StringField()
    year = IntField()
    school = StringField(choices=[s.value for s in Campus])
    description = StringField()
