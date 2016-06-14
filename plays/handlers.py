# -*- coding: utf-8 -*-
from flask import jsonify, Blueprint
from werkzeug.exceptions import HTTPException
from .exceptions import PlaysException
import logging
logger = logging.getLogger()

handlers = Blueprint('handlers', __name__)


# Handle custom exceptions that already have an error list
@handlers.app_errorhandler(PlaysException)
def handler(e):
    response = jsonify(code=e.code, errors=e.errors, result=None)
    response.status_code = e.code
    return response


# Handle other kinds of exceptions
@handlers.app_errorhandler(Exception)
def handler(e):
    code = e.code if isinstance(e, HTTPException) else 500

    response = jsonify(code=code, errors=[str(e)], result=None)
    response.status_code = code
    return response


# TODO: DRY. How to refactor these handlers?
@handlers.app_errorhandler(400)
def bad_request(e):
    return handler(e)


@handlers.app_errorhandler(404)
def bad_requestx(e):
    return handler(e)


@handlers.app_errorhandler(500)
def bad_requestx(e):
    return handler(e)
