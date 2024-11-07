from mongoengine import Document, DateTimeField, ObjectIdField
from datetime import datetime, timezone

class BaseDocument(Document):
    meta = {'abstract': True}

    id = ObjectIdField(primary_key=True, required=True)
    created_date = DateTimeField(default=lambda: datetime.now(timezone.utc))
    last_modified_date = DateTimeField(default=lambda: datetime.now(timezone.utc))

    def save(self, *args, **kwargs):
        if not self.created_date:
            self.created_date = datetime.now(timezone.utc)
        self.last_modified_date = datetime.now(timezone.utc)
        return super(BaseDocument, self).save(*args, **kwargs)
