# coding:utf8
from flask import Blueprint

admin = Blueprint("admin", __name__)

import movie_app.admin.views
