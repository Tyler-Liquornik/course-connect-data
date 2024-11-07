from mongoengine import ListField, ObjectIdField, StringField, IntField
from linkedin_scraper.document.base_document import BaseDocument
from linkedin_scraper.document.enums.breadth_category import BreadthCategory
from linkedin_scraper.document.enums.school import School

class Course(BaseDocument):
    meta = {'collection': 'courses'}

    course_outline_ids = ListField(ObjectIdField())
    number = IntField()
    suffix = ListField(StringField())
    subject_id = ObjectIdField()
    description = StringField()
    breadth_category = StringField(choices=[c.value for c in BreadthCategory])
    school = StringField(choices=[s.value for s in School])
