"""SQLAlchemy Metadata"""
from sqlalchemy import MetaData
from buildapi.model.buildapidb import Base

__all__ = ['scheduler_db_meta', 'status_db_meta', 'buildapi_db_meta']

scheduler_db_meta = MetaData()
status_db_meta = MetaData()
buildapi_db_meta = Base.metadata
