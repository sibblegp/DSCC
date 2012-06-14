__author__ = 'gsibble'

import datetime
import logging
from operator import attrgetter

from sqlalchemy import Column, ForeignKey, Integer, Text, Boolean, VARCHAR, DateTime, Float
from sqlalchemy import create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, relationship, backref, sessionmaker

import settings_debug as settings

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

DeclarativeBase = declarative_base()

DSCC_SQL_ENGINE = create_engine(settings.MYSQL_CONNECTION)
DSCC_SQL_SESSION = sessionmaker(bind=DSCC_SQL_ENGINE, autocommit=False, expire_on_commit=False, autoflush=True, twophase=True)()

DSCC_SQL_METADATA = DeclarativeBase.metadata
DSCC_SQL_METADATA.bind = DSCC_SQL_ENGINE

#
#   Core Functions
#

core_read = DSCC_SQL_SESSION.query
core_commit = DSCC_SQL_SESSION.commit

def core_add(object):
    DSCC_SQL_SESSION.add(object)
    DSCC_SQL_SESSION.commit()

def core_delete(object):
    DSCC_SQL_SESSION.delete(object)
    DSCC_SQL_SESSION.commit()

#
#  Models
#

class TropoSession(DeclarativeBase):
    __tablename__ = 'tropo_sessions'

    #Columns
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    tropo_session_id = Column(VARCHAR(length=100), nullable=False)
    tropo_call_id = Column(VARCHAR(length=100), nullable=False)
    started = Column(DateTime, nullable=False, default=datetime.datetime.utcnow())
    ended = Column(DateTime)
    updated = Column(DateTime, nullable=False, default=datetime.datetime.utcnow())

    #Foreign Keys
    conference_call_id = Column(Integer, ForeignKey('conference_calls.id'), nullable=True)

    def save(self):
        self.updated = datetime.datetime.utcnow()
        core_add(self)
        core_commit()

class ConferenceInitiator(DeclarativeBase):
    __tablename__ = 'conference_initiator'

    #Columns
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(VARCHAR(length=100), nullable=False)
    number = Column(VARCHAR(length=20), nullable=False)

class ConferenceMember(DeclarativeBase):
    __tablename__ = 'conference_member'
    
    #Columns
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(VARCHAR(length=100), nullable=False)
    number = Column(VARCHAR(length=20), nullable=False)

    #Foreign Keys
    conference_call_id = Column(Integer, ForeignKey('conference_calls.id'), nullable=True)

class ConferenceCall(DeclarativeBase):
    __tablename__ = 'conference_calls'

    #Columns
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    tropo_conference_id = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    dial_in_number = Column(VARCHAR(length=20), nullable=False)

    #Foreign Keys
    initiator_id = Column(Integer, ForeignKey('conference_initiator.id'), nullable=False)

    #Relationships
    initiator = relationship('ConferenceInitiator', backref='conference_call')
    members = relationship('ConferenceMember', backref='conference_call')
    sessions = relationship('TropoSession', backref='conference_call')

def initialize_sql():
    print "Dropping metadata..."
    DSCC_SQL_METADATA.drop_all(WC_SQL_ENGINE)

    print "Creating metadata..."
    DSCC_SQL_METADATA.create_all(WC_SQL_ENGINE)
