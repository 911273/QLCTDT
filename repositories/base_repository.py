# repositories/base_repository.py

class BaseRepository:
    def __init__(self, db):
        self.db = db
        # For convenience, expose the underlying connection if needed, 
        # but children should ideally use self.db methods
        self.conn = db.conn
