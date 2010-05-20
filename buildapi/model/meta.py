"""SQLAlchemy Metadata"""
from sqlalchemy import MetaData

__all__ = ['scheduler_db_meta', 'status_db_meta']

scheduler_db_meta = MetaData()
status_db_meta = MetaData()
