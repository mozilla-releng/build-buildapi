"""The application's model objects"""
from buildapi.model.meta import buildapi_db_meta
from buildapi.model.meta import scheduler_db_meta
from buildapi.model.meta import status_db_meta

def init_scheduler_model(engine):
    scheduler_db_meta.reflect(bind=engine)
    scheduler_db_meta.bind = engine

def init_status_model(engine):
    status_db_meta.reflect(bind=engine)
    status_db_meta.bind = engine

def init_buildapi_model(engine):
    buildapi_db_meta.bind = engine
    buildapi_db_meta.create_all()
