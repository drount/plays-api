# -*- coding: utf-8 -*-
from flask import Flask, jsonify
from flask_marshmallow import Marshmallow

from config import config

ma = Marshmallow()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    ma.init_app(app)

    # DB Endpoint
    from .db import db as db_blueprint
    from .db import init_db_blueprint
    app.register_blueprint(db_blueprint, url_prefix='')
    init_db_blueprint()
   
    # API Endpoints
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='')

    # Logging
    import logging
    import logging.config
    import yaml
    logging.config.dictConfig(yaml.load(open('logging.yml')))

    # Error Handling
    from .handlers import handlers as handlers_blueprint
    app.register_blueprint(handlers_blueprint, url_prefix='')

    return app
