from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base

from buildapi.lib import json

Base = declarative_base()

class JobRequest(Base):
    __tablename__ = 'jobrequests'
    #__table_args__ = (
            #UniqueConstraint('action', 'who', 'when'),
            #{},
            #)

    id = Column(Integer, primary_key=True)

    action = Column(String(20), nullable=False)
    who = Column(String, nullable=False)
    when = Column(Integer, nullable=False) # epoch timestamp
    completed_at = Column(Integer) # epoch timestamp

    # Extra data
    what = Column(String, nullable=False) # json blob

    # Extra data on completion
    complete_data = Column(String) # json blob

    def asDict(self):
        return dict(action=self.action,
                    who=self.who,
                    when=self.when,
                    completed_at=self.completed_at,
                    complete_data=self.complete_data,
                    what=json.loads(self.what))
