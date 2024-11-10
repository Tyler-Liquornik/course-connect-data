from mongoengine import StringField, IntField, URLField, DateField
from linkedin_scraper.document.base_document import BaseDocument



class JobDocument(BaseDocument):
    meta = {'collection': 'jobs'}

    linkedin_job_id = IntField(required=True, unique=True)
    linkedin_url = URLField(required=True)
    job_title = StringField()
    company = StringField()
    company_linkedin_url = URLField()
    location = StringField()
    posted_date = DateField()
    job_description = StringField()