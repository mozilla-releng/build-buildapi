"""The application's model objects"""
from buildapi.model.meta import scheduler_db_meta, status_db_meta


def init_scheduler_model(engine):
    scheduler_db_meta.reflect(bind=engine)
    scheduler_db_meta.bind = engine

def init_status_model(engine):
    status_db_meta.reflect(bind=engine)
    status_db_meta.bind = engine
