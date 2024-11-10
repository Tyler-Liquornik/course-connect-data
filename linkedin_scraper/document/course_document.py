from mongoengine import ListField, ObjectIdField, StringField, IntField
from linkedin_scraper.document.base_document import BaseDocument
from linkedin_scraper.document.enums.campus import Campus


class CourseDocument(BaseDocument):
    meta = {'collection': 'courses'}

    subject_id = ObjectIdField()
    course_outline_ids = ListField(ObjectIdField())
    number = IntField()
    suffix = ListField(StringField())
    description = StringField()
    campus = StringField(choices=[s.value for s in Campus])
