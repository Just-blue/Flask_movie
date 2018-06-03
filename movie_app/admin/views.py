# coding : utf8
import datetime
import uuid
from functools import wraps
import os

from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from movie_app import db,app
from . import admin
from flask import Flask, render_template, redirect, url_for, flash, session, request
from movie_app.admin.forms import LoginForm, TagForm, MovieForm, PreviewForm, PwdForm, AuthForm, RoleForm, AdminForm
from movie_app.models import Admin, Tag, Movie, Preview, User, Oplog, Adminlog, Userlog, Auth, Role, Moviecol, Comment


# 登陆装饰器
def admin_login_req(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if  "admin" not in session :
            return redirect(url_for("admin.login",next=request.url))
        return f(*args,**kwargs)

    return decorated_function

@admin.route("/")
@admin_login_req
def index():
    return render_template("admin/index.html")


@admin.route("/login/",methods = ['POST','GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = form.data
        admin = Admin.query.filter_by(name=data['account']).first()
        if not admin.check_pwd(data["pwd"]):
            flash("密码错误！","err")
            return redirect(url_for("admin.login"))
        session["admin"] = data["account"]
        session["admin_id"] = admin.id
        adminlog = Adminlog(
            admin_id=admin.id,
            ip=request.remote_addr
        )
        db.session.add(adminlog)  # 保存管理员登录日志
        db.session.commit()
        return redirect(request.args.get("next") or url_for("admin.index"))
    return render_template("admin/login.html",form = form)


@admin.route("/logout/")
@admin_login_req
def logout():
    session.pop("admin",None)
    session.pop("admin_id", None)
    return redirect(url_for("admin.login"))


#修改密码
@admin.route("/pwd/",methods =["GET","POST"])
@admin_login_req
def pwd():
    form = PwdForm()
    if form.validate_on_submit():
        data = form.data
        if not data["new_pwd"] == data["old_pwd"]:
            admin = Admin.query.filter_by(name=session["admin"]).first()
            admin.pwd = generate_password_hash(data["new_pwd"])
            db.session.add(admin)
            db.session.commit()
            flash("修改密码成功，请重新登录！", "ok")
            return redirect(url_for("admin.logout"))
        flash("密码不应与原密码相同！")
    return render_template("admin/pwd.html", form=form)


#添加标签
@admin.route("/tag_add/",methods = ['POST','GET'])
@admin_login_req
def tag_add():
    form = TagForm()
    if  form.validate_on_submit():
        data = form.data
        tag = Tag.query.filter_by(name=data['name']).count()
        if tag == 1:
            flash("标签已存在！",'error')
            return redirect(url_for('admin.tag_add'))
        tag = Tag(
            name = data["name"]
        )
        db.session.add(tag)
        db.session.commit()
        flash("添加成功",'ok')
        oplog = Oplog(
            admin_id=session["admin_id"],
            ip=request.remote_addr,
            reason="添加标签%s" % data["name"],
        )
        db.session.add(oplog)  # 操作日志
        db.session.commit()
        redirect(url_for('admin.tag_add'))
    return render_template("admin/tag_add.html",form=form)


#标签列表
@admin.route("/tag_list/<int:page>/",methods =["GET"])
@admin_login_req
def tag_list(page=None):
    if page is None:
        page = 1
    page_data = Tag.query.order_by(
        Tag.addtime.desc()
    ).paginate(page=page,per_page=10)
    return render_template("admin/tag_list.html",page_data=page_data)


# 标签修改
@admin.route("/tag/edit/<int:id>", methods=['GET', 'POST'])
@admin_login_req
def tag_edit(id=None):
    form = TagForm()
    tag = Tag.query.get_or_404(id)
    if form.validate_on_submit():
        data = form.data
        tag_count = Tag.query.filter_by(name=data["name"]).count()
        if tag.name == data["name"] and tag_count == 1:
            flash("名称已经存在！", "err")
            return redirect(url_for("admin.tag_edit", id=id))
        tag.name = data["name"]
        db.session.add(tag)
        db.session.commit()
        flash("修改标签成功", "ok")
        redirect(url_for("admin.tag_edit", id=id))
    return render_template("admin/tag_edit.html", form=form, tag=tag)



# 标签删除
@admin.route("/tag/del/<int:id>/", methods=["GET"])
@admin_login_req
def tag_del(id=None):
    tag = Tag.query.filter_by(id=id).first_or_404()
    db.session.delete(tag)
    db.session.commit()
    flash("删除标签成功！", "ok")
    return redirect(url_for('admin.tag_list', page=1))


# 修改文件名称
def change_filename(filename):
    fileinfo = os.path.splitext(filename)
    filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().hex) + fileinfo[-1]
    return filename

#添加电影
@admin.route("/movie_add/",methods = ["POST","GET"])
@admin_login_req
def movie_add():
    form = MovieForm()
    if form.validate_on_submit():
        data = form.data
        file_url = secure_filename(form.url.data.filename)
        file_logo = secure_filename(form.logo.data.filename)
        if not os.path.exists(app.config["UP_DIR"]):
            os.makedirs(app.config["UP_DIR"])
            os.chmod(app.config["UP_DIR"], "rw")
        url = change_filename(file_url)
        logo = change_filename(file_logo)
        form.url.data.save(app.config["UP_DIR"] + url)
        form.logo.data.save(app.config["UP_DIR"] + logo)
        movie = Movie(
            title=data["title"],
            url=url,
            info=data["info"],
            logo=logo,
            star=int(data["star"]),
            playnum=0,
            commentnum=0,
            tag_id=int(data["tag_id"]),
            area=data["area"],
            release_time=data["release_time"],
            length=data["length"]
        )
        db.session.add(movie)
        db.session.commit()
        flash("添加电影成功！", "ok")
        return redirect(url_for('admin.movie_add'))
    return render_template("admin/movie_add.html", form=form)


#电影列表
@admin.route("/movie_list/<int:page>/", methods=["GET"])
@admin_login_req
def movie_list(page=None):
    if page is None:
        page = 1
    page_data = Movie.query.join(Tag).filter(
        Tag.id == Movie.tag_id
    ).order_by(
        Movie.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/movie_list.html", page_data=page_data)


# 编辑电影
@admin.route("/movie/edit/<int:id>/", methods=["GET", "POST"])
@admin_login_req
def movie_edit(id=None):
    form = MovieForm()
    form.url.validators = []
    form.logo.validators = []
    movie = Movie.query.get_or_404(id)
    if request.method == "GET":
        form.info.data = movie.info
        form.tag_id.data = movie.tag_id
        form.star.data = movie.star
    if form.validate_on_submit():
        data = form.data
        movie_count = Movie.query.filter_by(title=data["title"]).count()

        if movie_count == 1 and movie.title != data["title"]:
            flash("片名已经存在！", "err")
            return redirect(url_for("admin.movie_edit", id=id))

        if not os.path.exists(app.config["UP_DIR"]):
            os.makedirs(app.config["UP_DIR"])
            os.chmod(app.config["UP_DIR"], "rw")

        if form.url.data.filename != "":
            file_url = secure_filename(form.url.data.filename)
            movie.url = change_filename(file_url)
            form.url.data.save(app.config["UP_DIR"] + movie.url)

        if form.logo.data.filename != "":
            file_logo = secure_filename(form.logo.data.filename)
            movie.logo = change_filename(file_logo)
            form.logo.data.save(app.config["UP_DIR"] + movie.logo)

        movie.title = data["title"]
        movie.info = data["info"]
        movie.star = data["star"]
        movie.tag_id = data["tag_id"]
        movie.area = data["area"]
        movie.length = data["length"]
        movie.release_time = data["release_time"]
        db.session.add(movie)
        db.session.commit()
        flash("修改电影成功！", "ok")
        return redirect(url_for('admin.movie_list', page=1))
    return render_template("admin/movie_edit.html", form=form, movie=movie)


# 删除电影
@admin.route("/movie_del/<int:id>/", methods=["GET"])
@admin_login_req
def movie_del(id=None):
    movie_del = Movie.query.get_or_404(int(id))
    db.session.delete(movie_del)
    db.session.commit()
    flash("删除电影成功！", "ok")
    return redirect(url_for("admin.movie_list", page=1))


#添加预告
@admin.route("/preview_add/",methods = ["GET","POST"])
@admin_login_req
def preview_add():
    form = PreviewForm()
    if form.validate_on_submit():
        data = form.data
        file_logo = secure_filename(form.logo.data.filename)
        if not os.path.exists(app.config["UP_DIR"]):
            os.makedirs(app.config["UP_DIR"])
            os.chmod(app.config["UP_DIR"], "rw")
        logo = change_filename(file_logo)
        form.logo.data.save(app.config["UP_DIR"] + logo)
        preview = Preview(
            title=data["title"],
            logo=logo
        )
        db.session.add(preview)
        db.session.commit()
        flash("添加预告成功！", "ok")
        return redirect(url_for('admin.preview_list',page=1))
    return render_template("admin/preview_add.html",form = form)



# 上映预告列表
@admin.route("/preview/list/<int:page>/", methods=["GET"])
@admin_login_req
def preview_list(page=None):
    if page is None:
        page = 1
    page_data = Preview.query.order_by(
        Preview.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/preview_list.html", page_data=page_data)


# 上映预告编辑
@admin.route("/preview/edit/<int:id>/", methods=["GET", "POST"])
@admin_login_req
def preview_edit(id):
    form = PreviewForm()
    form.logo.validators = []
    preview = Preview.query.get_or_404(int(id))
    if request.method == "GET":
        form.title.data = preview.title
    if form.validate_on_submit():
        data = form.data
        if form.logo.data.filename != "":
            file_logo = secure_filename(form.logo.data.filename)
            preview.logo = change_filename(file_logo)
            form.logo.data.save(app.config["UP_DIR"] + preview.logo)
        preview.title = data["title"]
        db.session.add(preview)
        db.session.commit()
        flash("修改预告成功！", "ok")
        return redirect(url_for('admin.preview_edit', id=id))
    return render_template("admin/preview_edit.html", form=form, preview=preview)


# 删除预告
@admin.route("/preview_del/<int:id>/", methods=["GET"])
@admin_login_req
def preview_del(id=None):
    preview = Preview.query.get_or_404(int(id))
    db.session.delete(preview)
    db.session.commit()
    flash("删除预告成功！", "ok")
    return redirect(url_for("admin.preview_list", page=1))


# 会员查看
@admin.route("/user/view/<int:id>/", methods=['GET'])
@admin_login_req
def user_view(id=None):
    user = User.query.get_or_404(int(id))
    return render_template("admin/user_view.html", user=user)


# 会员删除
@admin.route("/user/del/<int:id>/", methods=['GET'])
@admin_login_req
def user_del(id=None):
    user = User.query.get_or_404(int(id))
    db.session.delete(user)
    db.session.commit()
    flash("删除会员成功！", 'ok')
    return redirect(url_for('admin.user_list', page=1))



# 评论列表
@admin.route("/comment/list/<int:page>", methods=['GET'])
@admin_login_req
def comment_list(page=None):
    if page is None:
        page = 1
    page_data = Comment.query.join(Movie).join(User).filter(
        Movie.id == Comment.movie_id,
        User.id == Comment.user_id
    ).order_by(
        Comment.addtime.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    return render_template("admin/comment_list.html", page_data=page_data)

# 会员列表
@admin.route("/user/list/<int:page>/", methods=['GET'])
@admin_login_req
def user_list(page=None):
    if page is None:
        page = 1
    page_data = User.query.order_by(
        User.id.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    return render_template("admin/user_list.html", page_data=page_data)


# 评论删除
@admin.route("/comment/del/<int:id>", methods=['GET'])
@admin_login_req
def comment_del(id=None):
    comment = Comment.query.get_or_404(id)
    movie = Movie.query.filter(
        comment.movie_id == Movie.id
    ).first()
    movie.commentnum -= 1
    db.session.add(movie)
    db.session.commit()
    db.session.delete(comment)
    db.session.commit()
    flash("删除评论成功！", 'ok')
    return redirect(url_for('admin.comment_list', page=1))


# 收藏列表
@admin.route("/moviecol/list/<int:page>", methods=['GET'])
@admin_login_req
def moviecol_list(page=None):
    if page is None:
        page = 1
    page_data = Moviecol.query.join(Movie).join(User).filter(
        Movie.id == Moviecol.movie_id,
        User.id == Moviecol.user_id
    ).order_by(
        Moviecol.id.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    return render_template("admin/moviecol_list.html", page_data=page_data)


# 收藏删除
@admin.route("/moviecol/del/<int:id>", methods=['GET'])
def moviecol_del(id=None):
    moviecol = Moviecol.query.get_or_404(id)
    db.session.delete(moviecol)
    db.session.commit()
    flash("删除评论成功！", 'ok')
    return redirect(url_for('admin.moviecol_list', page=1))


# 操作日志列表
@admin.route("/oplog/list/<int:page>/", methods=["GET"])
@admin_login_req
def oplog_list(page=None):
    if page is None:
        page = 1
    page_data = Oplog.query.join(Admin).filter(
        Admin.id == Oplog.admin_id).order_by(
        Oplog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/oplog_list.html", page_data=page_data)

# 管理员日志列表
@admin.route("/adminloginlog/list/<int:page>/", methods=["GET"])
@admin_login_req
def adminloginlog_list(page=None):
    if page is None:
        page = 1
    page_data = Adminlog.query.join(Admin).filter(
        Admin.id == Adminlog.admin_id).order_by(
        Adminlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/adminloginlog_list.html", page_data=page_data)


# 会员日志列表
@admin.route("/userloginlog/list/<int:page>/", methods=["GET"])
@admin_login_req
def userloginlog_list(page=None):
    if page is None:
        page = 1
    page_data = Userlog.query.join(
        User).filter(
        User.id == Userlog.user_id).order_by(
        Userlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/userloginlog_list.html", page_data=page_data)


#角色添加
@admin.route("/role_add/", methods=["GET", "POST"])
@admin_login_req
def role_add():
    form = RoleForm()
    if form.validate_on_submit():
        data = form.data
        role = Role(
            name=data["name"],
            auths=",".join(map(lambda v: str(v), data["auths"]))  # map(f,data) 等同于 [f(x) for x in data ]
        )
        db.session.add(role)
        db.session.commit()
        flash("添加角色成功！", "ok")
    return render_template("admin/role_add.html", form=form)


# 角色删除
@admin.route("/role/del/<int:id>/", methods=["GET"])
@admin_login_req

def role_del(id=None):
    role = Role.query.filter_by(id=id).first_or_404()
    db.session.delete(role)
    db.session.commit()
    flash("删除角色成功！", "ok")
    return redirect(url_for('admin.role_list', page=1))


# 角色修改
@admin.route("/role/edit/<int:id>/", methods=["GET", "POST"])
@admin_login_req

def role_edit(id=None):
    form = RoleForm()
    role = Role.query.get_or_404(id)
    auths = role.auths
    form.auths.data = list(map(lambda v: int(v), auths.split(",")))
    if form.validate_on_submit():
        data = form.data
        role.name = data["name"]
        role.auths = ",".join(map(lambda v: str(v), data["auths"]))
        db.session.add(role)
        db.session.commit()
        flash("修改角色成功！", "ok")
    return render_template("admin/role_edit.html", form=form, role=role)


# 角色列表
@admin.route("/role/list/<int:page>/", methods=["GET"])
@admin_login_req
def role_list(page=None):
    if page is None:
        page = 1
    page_data = Role.query.order_by(
        Role.addtime.desc()).paginate(page=page, per_page=10)
    return render_template("admin/role_list.html", page_data=page_data)

#权限添加
@admin.route("/auth_add/", methods=["GET","POST"])
@admin_login_req
def auth_add():
    form = AuthForm()
    if form.validate_on_submit():
        data = form.data
        auth = Auth(
            name=data["name"],
            url=data["url"]
        )
        db.session.add(auth)
        db.session.commit()
        flash("添加权限成功！", "ok")
        oplog = Oplog(
            admin_id=session["admin_id"],
            ip=request.remote_addr,
            reason="添加权限%s" % data["name"],
        )
        db.session.add(oplog)  # 操作日志
        db.session.commit()
    return render_template("admin/auth_add.html",form=form)


# 修改权限
@admin.route("/auth_edit/<int:id>", methods=["GET","POST"])
@admin_login_req
def auth_edit(id=None):
    auth_data = Auth.query.get_or_404(id)
    form = AuthForm()
    if form.validate_on_submit():
        data = form.data
        auth_data.name = data["name"]
        auth_data.url = data["url"]
        db.session.add(auth_data)
        db.session.commit()
        flash("修改权限成功！", "ok")
        oplog = Oplog(
            admin_id=session["admin_id"],
            ip=request.remote_addr,
            reason="修改权限%s" % data["name"],
        )
        db.session.add(oplog)  # 操作日志
        db.session.commit()
        return redirect(url_for("admin.auth_list", page=1))
    return render_template("admin/auth_edit.html",form=form,page_data = auth_data)


# 权限删除
@admin.route("/auth/del/<int:id>/", methods=["GET"])
@admin_login_req
def auth_del(id=None):
    auth = Auth.query.get_or_404(id)
    db.session.delete(auth)
    db.session.commit()
    flash("删除权限成功！", "ok")
    return redirect(url_for("admin.auth_list", page=1))


# 权限列表
@admin.route("/auth/list/<int:page>/", methods=["GET"])
@admin_login_req
def auth_list(page=None):
    if page is None:
        page = 1
    page_data = Auth.query.order_by(
        Auth.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/auth_list.html", page_data=page_data)



# 管理员添加
@admin.route("/admin_add/", methods=["GET", "POST"])
@admin_login_req
def admin_add():
    form = AdminForm()
    if form.validate_on_submit():
        data = form.data
        from werkzeug.security import generate_password_hash
        admin = Admin(
            name=data["name"],
            pwd=generate_password_hash(data["pwd"]),
            role_id=data["role_id"],
            is_super=1
        )
        db.session.add(admin)
        db.session.commit()
        flash("添加管理员成功！", "ok")
    return render_template("admin/admin_add.html", form=form)



# 管理员列表
@admin.route("/admin_list/<int:page>/", methods=["GET"])
@admin_login_req
def admin_list(page=None):
    if page is None:
        page = 1
    page_data = Admin.query.join(Role).filter(
        Role.id == Admin.role_id).order_by(
        Admin.addtime.desc()).paginate(page=page, per_page=10)
    return render_template("admin/admin_list.html", page_data=page_data)
