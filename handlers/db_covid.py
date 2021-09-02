from pathlib import Path
import os
import time
import math
import datetime
from datetime import datetime, timedelta
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Boolean, Integer, String, Float, SmallInteger, \
        BigInteger, ForeignKey, Index, UniqueConstraint, \
        create_engine, cast, func, desc, asc, desc, and_, exists, text, distinct
from sqlalchemy.orm import sessionmaker, relationship, eagerload, foreign, remote, scoped_session
from sqlalchemy.types import TypeDecorator, Numeric, Text, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func
from sqlalchemy import and_, or_
from logging import basicConfig, getLogger, FileHandler, StreamHandler, DEBUG, INFO, ERROR, Formatter
from geopy.distance import geodesic
from sys import argv
import importlib
import json
LOG = getLogger('__name__')

config = importlib.import_module('handlers.config')

if config.DB_ENGINE.startswith('mysql'):
    from sqlalchemy.dialects.mysql import TINYINT, MEDIUMINT, BIGINT, DOUBLE, LONGTEXT

    TINY_TYPE = TINYINT(unsigned=True)          # 0 to 255
    MEDIUM_TYPE = Integer                       # 0 to 4294967295
    UNSIGNED_HUGE_TYPE = BIGINT(unsigned=True)  # 0 to 18446744073709551615
    HUGE_TYPE = BigInteger
    PRIMARY_HUGE_TYPE = HUGE_TYPE 
    FLOAT_TYPE = DOUBLE(precision=18, scale=14, asdecimal=False)
    LONG_TEXT = LONGTEXT
elif config.DB_ENGINE.startswith('postgres'):
    from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, TEXT

    class NumInt(TypeDecorator):
        '''Modify Numeric type for integers'''
        impl = Numeric

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            return int(value)

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            return int(value)

        @property
        def python_type(self):
            return int

    TINY_TYPE = SmallInteger                    # -32768 to 32767
    MEDIUM_TYPE = Integer                       # -2147483648 to 2147483647
    UNSIGNED_HUGE_TYPE = NumInt(precision=20, scale=0)   # up to 20 digits
    HUGE_TYPE = BigInteger
    PRIMARY_HUGE_TYPE = HUGE_TYPE 
    FLOAT_TYPE = DOUBLE_PRECISION(asdecimal=False)
    LONG_TEXT = TEXT
else:
    class TextInt(TypeDecorator):
        '''Modify Text type for integers'''
        impl = Text

        def process_bind_param(self, value, dialect):
            return str(value)

        def process_result_value(self, value, dialect):
            return int(value)

    TINY_TYPE = SmallInteger
    MEDIUM_TYPE = Integer
    UNSIGNED_HUGE_TYPE = TextInt
    HUGE_TYPE = Integer
    PRIMARY_HUGE_TYPE = HUGE_TYPE 
    FLOAT_TYPE = Float(asdecimal=False)

Base = declarative_base()
engine = create_engine(config.DB_ENGINE, pool_recycle=150, pool_size=config.POOL_SIZE, pool_pre_ping=True)


class Schools(Base):
    __tablename__ = 'schools'

    id = Column(MEDIUM_TYPE, primary_key=True)
    school = Column(String)
    school_type = Column(String(128))
    principal = Column(String(128))
    address = Column(String(128))
    county = Column(String(128))
    city = Column(String(128))
    state = Column(String(128))
    zip_code = Column(String(128))
    lat = Column(FLOAT_TYPE)
    lon = Column(FLOAT_TYPE)
    phone = Column(String(128))
    district = Column(Integer)
#    student_case = relationship("Cases"(Schools.school==Cases.school_name)")

class Cases(Base):
    __tablename__ = 'cases'

    id = Column(PRIMARY_HUGE_TYPE, primary_key=True)
    school_name = Column(MEDIUM_TYPE)
    student = Column(TINY_TYPE)
    employee = Column(TINY_TYPE)
    other = Column(TINY_TYPE)
    date_reported = Column(MEDIUM_TYPE)
    notes = Column(String(128))

class Admins(Base):
    __tablename__ = 'users'

    id = Column(HUGE_TYPE, primary_key=True)
    user = Column(String(250))
    password = Column(String(250))
    access_level = Column(TINY_TYPE)
    expire_timestamp = Column(Integer)
    session_id = Column(String(100))

Session = sessionmaker(bind=engine)

@contextmanager
def session_scope(autoflush=False):
    """Provide a transactional scope around a series of operations."""
    session = Session(autoflush=autoflush)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()



def county_list(session):
    counties = session.query(distinct(Schools.county)). \
        order_by(Schools.county).all()
    return counties

def get_schools_type(session, type='all'):
    if type == 'all':
        schools = session.query(Schools.school, Schools.school_type, func.sum(Cases.student).label('students'), \
            func.sum(Cases.employee).label('employees')). \
                join(Cases, Schools.school == Cases.school_name). \
                    order_by(Schools.school).scalar()
    else:
        schools = session.query(Schools, \
            func.sum(Cases.student).label('students'), \
            func.sum(Cases.employee).label('employees')). \
                join(Cases). \
                    filter(school_type==type). \
                        group_by(school_type).scalar()
    return schools

#BACKEND SCHOOL LIST QUERY
def get_all_schools(session):
    schools = session.query(Schools.school).all()

    return schools

#LEAFLET MARKERS
def get_school_loc(session, name='All'):
    if name == 'All':
        school_markers = session.query(Schools). \
            group_by(Schools.school_type, Schools.school)
    else:
        school_markers = session.query(Schools). \
           filter(Schools.school==name).one()
    return school_markers



def get_schools(session):
    schools = session.query(Cases.school_name, \
        func.sum(Cases.student).label('student'), \
           func.sum(Cases.employee).label('employee')). \
              group_by(Cases.school_name)
                # order_by(desc('student', 'employee'))
    return schools


def get_report(session, school_detail):
    school = session.query(Cases.school_name, Cases.date_reported, Cases.student, Cases.employee). \
               filter(Cases.school_name==school_detail). \
                       order_by(Cases.date_reported).all()
    return school




def add_case(session, school_name, student, employee, date_reported):
    session.add(Cases(school_name=school_name,student=student,employee=employee,date_reported=date_reported))
    success = ('Added ' + school_name + ' ' + date_reported)

    return success

# COUNTS
def get_today(session):
    current_date = datetime.now().strftime('%m-%d-%Y')
    todays_count = session.query((func.sum(Cases.employee) + func.sum(Cases.student)).label('totals')). \
        filter(Cases.date_reported==current_date).scalar()
    if todays_count is None:
        current_date = datetime.now()
        day = timedelta(1)
        current_date = (current_date - day).strftime('%m-%d-%Y')
        todays_count = session.query((func.sum(Cases.employee) + func.sum(Cases.student)).label('totals')). \
            filter(Cases.date_reported==current_date).scalar()

    return todays_count


def get_today_cases(session):
#    current_date = datetime.now().strftime('%m-%d-%Y')
    current_date = last_update(session)
    todays_cases = session.query(distinct(Cases.school_name), func.sum(Cases.student).label('student'), \
         func.sum(Cases.employee).label('employee')). \
            filter(Cases.date_reported==current_date). \
               group_by(Cases.school_name)
    if todays_cases is None:
        current_date = datetime.now()
        day = timedelta(1)
        current_date = (current_date - day).strftime('%m-%d-%Y')
        todays_cases = session.query(distinct(Cases.school_name), func.sum(Cases.student).label('student'), \
            func.sum(Cases.employee).label('employee')). \
                filter(Cases.date_reported==current_date). \
                    group_by(Cases.school_name)

    return todays_cases


def last_update(session):
    last_day = session.query(Cases).order_by(desc(Cases.date_reported)).first()
    latest = last_day.date_reported

    return latest


def get_weeks(session):
    current_date = datetime.now() - timedelta(13)
    x = 0
    date_array = ''
    count_array = ''
    for x in range(14):
        day = timedelta(x)
        new_date = ((current_date + day)).strftime('%m-%d-%Y')
        count = session.query((func.sum(Cases.employee) + func.sum(Cases.student).label('total'))). \
            filter(Cases.date_reported==new_date).scalar()
        if count == None:
            count = 0
        count_array += str(count) + ", "
        date_array += new_date[:-5].replace('-', '') + ", "
    date_array = ('[' + date_array[:-2] + ']')
    count_array = ('[' + count_array[:-2] + ']')

    return date_array, count_array

def get_all(session):
    date_array = ''
    count_array = ''
    dates = session.query(distinct(Cases.date_reported)).order_by(asc(Cases.date_reported))
    for d in dates:
        count = session.query((func.sum(Cases.employee) + func.sum(Cases.student).label('total'))). \
            filter(Cases.date_reported==d[0]).scalar()
        if count == None:
            count = 0
        count_array += str(count) + ", "
        date_array += d[0][:-5].replace('-', '') + ", "
    date_array = ('[' + date_array[:-2] + ']')
    count_array = ('[' + count_array[:-2] + ']')

    return date_array, count_array



#def district_totals(session):
#    districts = session.query(distinct(Schools.district), (func.sum(Cases.student) + func.sum(Cases.employee)).label('total')). \
#        join(Cases).filter(Schools.school==Cases.school_name). \
#            filter(Schools.district.isnot(None)). \
#                group_by(Schools.district). \
#                    order_by(desc('total'))

#    return districts

def student_total(session, school=None):
    if school is None:
        student_cases = session.query(func.sum(Cases.student)).scalar()
    else:
        student_cases = session.query(func.sum(Cases.student)). \
            filter(Cases.school==school).scalar()
    if student_cases is None:
        student_cases = 0
    return student_cases


def employee_total(session):
    employee_cases = session.query(func.sum(Cases.employee)).scalar()
    if employee_cases is None:
        employee_cases = 0
    return employee_cases


def get_count(session):
    current_date = datetime.now().strftime('%m-%d-%Y')
    cases = session.query(func.sum(Cases.student).label('total')). \
        filter(Cases.date_reported <= current_date). \
           order_by(Cases.date_reported).all()

    return cases


### Back-end User queries
def root_user(session):
    count = 0
    count = session.query(Admins).count()
    return count


def get_user(session, user_id):
    user = session.query(Admins).filter_by(id=user_id).first()
    return user


def check_user_exists(session, user, password):
    userData = None
    userData = session.query(Admins.password, Admins.id).filter_by(user=user).first()
    return userData


def add_user(session, user, password, access_level=0):
    msg = 'Error'
    access_level = 1 # 0 for not verified
    newuser = session.add(Admins(user=user,password=password,access_level=access_level))
    msg = 'Success! User added.'
    return msg
