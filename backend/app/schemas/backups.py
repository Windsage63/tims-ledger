from datetime import datetime

from pydantic import BaseModel


class BackupCreateRead(BaseModel):
    path: str
    created_at: datetime
    included_database: bool
    included_file_count: int
