from flask import Flask
from flask import request
from flask import jsonify, abort
from flask import flash
from flask import redirect, g
from flask import session as webSession
import datetime
import random
from logging import getLogger, basicConfig, INFO, WARNING, DEBUG, FileHandler, \
    StreamHandler, Formatter
import time
import requests
from werkzeug.security import check_password_hash, generate_password_hash
from handlers.router import router
from handlers import db_covid
from handlers.db_covid import check_user_exists, get_user

import os
import importlib
import datetime
import json

log = getLogger(__name__)
getLogger('werkzeug').setLevel(WARNING)
config = importlib.import_module('handlers.config')
log.warning('Port:{}'.format(config.PORT))



def create_app():
    app = Flask(__name__)
    app.register_blueprint(router)
    app.secret_key = config.SECRET_KEY

    return app


flask_app = create_app()


### PRELOAD USER FOR BLUEPRINT ###
@flask_app.before_request
def load_logged_in_user():
    user_id = webSession.get('user_id')
    if user_id is None:
        g.user = None
    else:
        with db_covid.session_scope() as session:
            g.user = get_user(session, user_id)




if __name__ == '__main__':
    flask_app.jinja_env.auto_reload = True
    flask_app.config['TEMPLATES_AUTO_RELOAD'] = True
    flask_app.run(host='0.0.0.0', port=int(config.PORT), threaded=True)
