from mongoengine import StringField, IntField
from linkedin_scraper.document.base_document import BaseDocument
from linkedin_scraper.document.enums.school import School

class CourseOutline(BaseDocument):
    meta = {'collection': 'course_outlines'}

    code = StringField()
    year = IntField()
    school = StringField(choices=[s.value for s in School])
    description = StringField()
