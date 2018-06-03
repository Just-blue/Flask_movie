# coding : utf8
import uuid,json
from functools import wraps
import os
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from movie_app import db, app
from movie_app.admin.views import change_filename
from movie_app.home.forms import RegistForm, LoginForm, UserdetailForm, PwdForm, CommentForm
from movie_app.models import User, Userlog, Tag, Movie, Comment, Moviecol
from . import home
from flask import render_template, redirect, url_for, flash, session, request


# 登陆装饰器
def uesr_login_req(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if  "user" not in session :
            return redirect(url_for("home.login",next=request.url))
        return f(*args,**kwargs)

    return decorated_function

# 首页
@home.route('/<int:page>/', methods=["GET"])
def index(page=None):
    tags = Tag.query.all()
    page_data = Movie.query

    # 标签
    tid = request.args.get("tid", 0)
    if int(tid) != 0:
        page_data = page_data.filter_by(tag_id=int(tid))

    # 星级
    star = request.args.get("star", 0)
    if int(star) != 0:
        page_data = page_data.filter_by(star=int(star))

    # 时间
    time = request.args.get("time", 0)
    if int(time) != 0:
        if int(time) == 1:
            page_data = page_data.order_by(
                Movie.addtime.desc()
            )
        else:
            page_data = page_data.order_by(
                Movie.addtime.asc()
            )

    # 播放量
    pm = request.args.get("pm", 0)
    if int(pm) != 0:
        if int(pm) == 1:
            page_data = page_data.order_by(
                Movie.playnum.desc()
            )
        else:
            page_data = page_data.order_by(
                Movie.playnum.asc()
            )

    # 评论量
    cm = request.args.get("cm", 0)
    if int(cm) != 0:
        if int(cm) == 1:
            page_data = page_data.order_by(
                Movie.commentnum.desc()
            )
        else:
            page_data = page_data.order_by(
                Movie.commentnum.asc()
            )

    if page is None:
        page = 1
    page_data = page_data.paginate(page=page, per_page=8)

    p = dict(
        tid=tid,
        star=star,
        time=time,
        pm=pm,
        cm=cm
    )

    return render_template("home/index.html", p=p, tags=tags, page_data=page_data)



# 会员登陆
@home.route("/login/",methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = form.data
        user = User.query.filter_by(name=data['name']).first()
        if not user.check_pwd(data['pwd']):
            flash('密码错误!', 'err')
            return redirect(url_for('home.login'))
        session['user'] = user.name
        session['user_id'] = user.id

        # 更新数据库 内容
        userlog = Userlog(
            user_id=user.id,
            ip=request.remote_addr
        )
        db.session.add(userlog)
        db.session.commit()

        return redirect(url_for('home.user'))
    return render_template("home/login.html", form=form)


# 会员退出
@home.route("/logout/")
def logout():
    session.pop("user",None)
    session.pop("user_id",None)
    return redirect(url_for("home.login"))


# 注册会员
@home.route("/regist/", methods=["POST", "GET"])
def regist():
    form = RegistForm()
    if form.validate_on_submit():
        data = form.data
        user = User(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            pwd=generate_password_hash(data['pwd']),
            uuid=uuid.uuid4().hex
        )
        db.session.add(user)
        db.session.commit()
        flash('注册成功！', 'ok')
        return redirect(url_for('home.login'))
    return render_template("home/regist.html", form=form)


# 评论管理
@home.route("/comments/<int:page>")
@uesr_login_req
def comments(page=None):
    if page==None:
        page = 1
    comments = Comment.query.join(
        User).join(
        Movie
    ).filter(
        Movie.id == Comment.movie_id,
        User.id == session['user_id']
    ).order_by(
        Comment.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("home/comments.html",comments=comments)


# 评论删除
@home.route("/comments_del/<int:id>")
@uesr_login_req
def comments_del(id=None):
    comments = Comment.query.filter_by(id=id).first_or_404()
    movie = Movie.query.filter(comments.movie_id == Movie.id).first()
    movie.commentnum -= 1
    db.session.delete(comments)
    db.session.commit()
    db.session.add(movie)
    db.session.commit()
    flash("删除评论成功！", "ok")
    return redirect(url_for('home.comments', page=1))

# 登陆日志
@home.route("/loginlog/")
@uesr_login_req
def loginlog(page=None):
    if page is None:
        page = 1
    page_data = Userlog.query.filter_by(user_id=int(session['user_id'])).order_by(
        Userlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("home/loginlog.html", page_data=page_data)


# 添加电影收藏
@home.route('/moviecol_add/', methods=["GET"])
@uesr_login_req
def moviecol_add():
    uid = request.args.get("uid", "")
    mid = request.args.get("mid", "")
    moviecol = Moviecol.query.filter_by(
        user_id=int(uid),
        movie_id=int(mid)
    ).count()

    if moviecol == 1:
        data = dict(ok=0)

    if moviecol == 0:
        moviecol = Moviecol(
            user_id=int(uid),
            movie_id=int(mid)
        )
        db.session.add(moviecol)
        db.session.commit()
        data = dict(ok=1)

    return json.dumps(data)

# 收藏电影
@home.route('/moviecol/<int:page>/', methods=["GET"])
@uesr_login_req
def moviecol(page=None):
    if page is None:
        page = 1
    page_data = Moviecol.query.join(
        Movie
    ).join(
        User
    ).filter(
        Moviecol.movie_id == Movie.id,
        Moviecol.user_id == session["user_id"]
    ).order_by(
        Moviecol.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("home/moviecol.html", page_data=page_data)


# 修改密码
@home.route("/pwd/",methods=["GET","POST"])
@uesr_login_req
def pwd():
    form = PwdForm()
    user = User.query.get(session['user_id'])
    if form.validate_on_submit():
        data = form.data
        if not user.check_pwd(form.old_pwd.data):
            flash("原密码输错错误","err")
            return redirect(url_for('home.pwd'))
        user.pwd = generate_password_hash(data['new_pwd'])
        db.session.add(user)
        db.session.commit()
        flash("修改密码成功", "ok")
        return redirect(url_for('home.pwd'))
    return render_template("home/pwd.html",form=form)


# 修改账户信息
@home.route("/user/",methods=["GET","POST"])
@uesr_login_req
def user():
    form = UserdetailForm()
    user = User.query.filter_by(name=session['user']).first()
    form.face.validators = []
    if form.validate_on_submit():
        data = form.data
        file_face = secure_filename(form.face.data.filename)
        if not os.path.exists(app.config['FC_DIR']):
            os.makedirs(app.config['FC_DIR'])
            os.chmod(app.config['FC_DIR'], 'rw')
        user.face = change_filename(file_face)
        form.face.data.save(app.config['FC_DIR'] + user.face)

        name_count = User.query.filter_by(name=data['name']).count()
        if data['name'] != user.name and name_count == 1:
            flash('昵称已经存在！', 'err')
            return redirect(url_for('home.user'))

        email_count = User.query.filter_by(email=data['email']).count()
        if data['email'] != user.email and email_count == 1:
            flash('邮箱已经存在！', 'err')
            return redirect(url_for('home.user'))

        phone_count = User.query.filter_by(phone=data['phone']).count()
        if data['phone'] != user.phone and phone_count == 1:
            flash('手机号已经存在！', 'err')
            return redirect(url_for('home.user'))

        user.name = data['name']
        user.email = data['email']
        user.phone = data['phone']
        user.info = data['info']
        db.session.add(user)
        db.session.commit()
        flash('修改成功!', 'ok')
        return redirect(url_for('home.user'))
    return render_template("home/user.html",form=form,user = user)


@home.route("/animation/")
def animation():
    return render_template("home/animation.html")


# 电影搜索
@home.route('/search/<int:page>/')
def search(page=None):
    if page is None:
        page = 1
    key = request.args.get("key", "")
    movie_count = Movie.query.filter(
        Movie.title.ilike('%' + key + '%')
    ).count()
    page_data = Movie.query.filter(
        Movie.title.ilike('%' + key + '%')
    ).order_by(
        Movie.addtime.desc()
    ).paginate(page=page, per_page=10)
    page_data.key = key
    return render_template("home/search.html", page_data=page_data, key=key, movie_count=movie_count)


# 播放页面

@home.route('/play/<int:id>/<int:page>/', methods=["GET", "POST"])
def play(id=None, page=None):
    movie = Movie.query.join(
        Tag
    ).filter(
        Tag.id == Movie.tag_id,
        Movie.id == id
    ).first_or_404()
    if page is None:
        page = 1

    page_data = Comment.query.join(
        Movie
    ).join(
        User
    ).filter(
        movie.id == Comment.movie_id,
        # User.id == session['user_id']
    ).order_by(
        Comment.addtime.desc()
    ).paginate(page=page, per_page=10)

    movie.playnum += 1
    form = CommentForm()
    if "user" in session and form.validate_on_submit():
        data = form.data
        comment = Comment(
            content=data['content'],
            movie_id=movie.id,
            user_id=session['user_id']
        )
        db.session.add(comment)
        db.session.commit()
        movie.commentnum += 1
        db.session.add(movie)
        db.session.commit()
        flash('添加评论成功！', 'ok')
        return redirect(url_for("home.play", id=movie.id, page=1))
    db.session.add(movie)
    db.session.commit()
    return render_template("home/play.html", movie=movie, form=form,page_data=page_data)