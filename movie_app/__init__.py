# coding : utf8
import os
from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
#用于连接数据的数据库。
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:Ms121008@127.0.0.1:3306/movie"
#如果设置成 True (默认情况)，Flask-SQLAlchemy 将会追踪对象的修改并且发送信号。
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] =True
app.config['SECRET_KEY'] = 'pokker'
app.config["UP_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/")
app.config["FC_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/users/")

app.debug = True
db = SQLAlchemy(app)

from movie_app.home import home as home_Blueprint
from movie_app.admin import admin as admin_Blueprint

app.register_blueprint(home_Blueprint)
app.register_blueprint(admin_Blueprint, url_prefix="/admin")

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404/404.html"),404