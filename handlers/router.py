
from flask import Blueprint, render_template, abort
from flask import redirect, url_for, g
from flask import request, jsonify, make_response
#from flask import flash
from jinja2 import TemplateNotFound
from werkzeug.security import check_password_hash, generate_password_hash
from flask import session as webSession
from pkg_resources import resource_filename
import functools
import time
import datetime
import io
import csv
import json
from handlers import db_covid
from handlers.db_covid import Session, county_list, get_schools, get_schools_type, add_case, \
    check_user_exists, student_total, employee_total, get_weeks, get_count, get_all_schools, \
    get_today, get_weeks, get_today_cases, get_school_loc, last_update, get_report, get_all
import importlib
import ast
from datetime import datetime

config = importlib.import_module('handlers.config')

router =  Blueprint('router', __name__, url_prefix='/dash', template_folder='/templates')



def js_array(item_list):
    item_list = ('[' +  item_list[:-2] + ']')
    return item_list



##### START LOGIN/DASHBOARD BLUEPRINT #####
@router.route('/<page>')
def show(page):
    try:
        return render_template('templates/%s.html' % page)
    except TemplateNotFound:
        abort(404)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("router.login"))

        return view(**kwargs)

    return wrapped_view


@router.route('/')
def index():
    with db_covid.session_scope() as session:
        today = datetime.now().strftime('%m-%d-%Y')
        all_today = get_today_cases(session)
        cases = get_count(session)
        todays_total = get_today(session)
        counties = county_list(session)
        students = student_total(session)
        employees = employee_total(session)
        school_list_e = get_schools(session)
        date_array, count_array = get_weeks(session)
        date_array2, count_array2 = get_all(session)
        last_updated = last_update(session)

    return render_template("index.html", date_array2=date_array2, count_array2=count_array2, last_updated=last_updated, today=today, all_today=all_today, \
        count_array=count_array, date_array=date_array, todays_total=todays_total, cases=cases, \
            counties=counties ,students=students, employees=employees, school_list_e=school_list_e)


@router.route('/update', methods=('POST', 'GET'))
@login_required
def update():
    with db_covid.session_scope() as session:
        result = ''
        if request.method == 'POST':
            f = request.form
            school_name = f['school_name']
            student = f['student']
            employee = f['employee']
            date_reported = f['report_date']
            print(f)
        if student == '':
            student = 0
        if employee == '':
            employee = 0
        result = add_case(session, school_name, student, employee, date_reported)
        students = student_total(session)
        return redirect(url_for('router.newcases', result=result, students=students))


@router.route('/newcases')
@login_required
def newcases():
    current_date = datetime.now().strftime('%m-%d-%Y')
    with db_covid.session_scope() as session:
        counties = county_list(session)
        school_list = get_all_schools(session)
        students = student_total(session)
        employees = employee_total(session)

        return render_template("newcases.html", counties=counties, school_list=school_list, \
           students=students, employees=employees, current_date=current_date)


@router.route('/report', methods=('GET', 'POST'))
def report():
    detail = request.args.get('school')
    current_date = datetime.now().strftime('%m-%d-%Y')
    with db_covid.session_scope() as session:
        school_detail = get_report(session, detail)
        if detail == None:
            return redirect(url_for('router.index'))
        location = get_school_loc(session, detail)
        return render_template("report.html",location=location, detail=detail, school_detail=school_detail, current_date=current_date)

@router.route('/map', methods=('GET', 'POST'))
@login_required
def map():
    with db_covid.session_scope() as session:
        school_loc = get_school_loc(session)

        return render_template('map2.html', school_loc=school_loc)


@router.route('/login', methods=('GET', 'POST'))
def login():
    error = None
    with db_covid.session_scope() as session:
        if request.method == 'POST':
            user = request.form['username']
            password = request.form['password']
            userData = check_user_exists(session, user, password)
            if userData is None:
                error = 'Invalid Credentials.'
            elif not check_password_hash(userData[0], password):
                error = 'Invalid Credentials.'

            if error is None:
#                webSession.clear()
                webSession['user_id'] = userData[1]
                return redirect(url_for('router.newcases'))
        if error:
            return render_template('login.html', error=error)
        else:
            return render_template('login.html')


@router.route('/logout')
@login_required
def logout():
    webSession.pop('user_id', None)
    webSession.clear()
    g.user = None
    user_id = None
    user = None
    flash('You are now logged out')
    return redirect(url_for('router.login'))
 
# End Blueprint
