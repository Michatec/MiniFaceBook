from flask import Flask, request, render_template, redirect, url_for, flash, abort, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash
from flask_babel import Babel, gettext as _
from waitress import serve
from routes.admin import admin_bp
from routes.discord import discord_bp
from routes.post import post_bp
from routes.login import log_bp
from routes.support import support_bp
from routes.like import like_bp
from routes.profile import profile_bp
from routes.user import user_bp
from routes.friends import friends_bp
from routes.notifications import noti_bp
from routes.credits import credits_bp
from models import db, User, Reward, UserShopItem, ShopItem, SHOPITEM_ID_PREMIUM, SHOPITEM_ID_GOLDRAHMEN, SHOPITEM_ID_EXTRA_TYPES, SHOPITEM_ID_EXTRA_UPLOAD
try:
    from routes.oauth import oauth
except ImportError:
    pass
import re
import os

__mapper_args__ = {"confirm_deleted_rows": False}

app = Flask(__name__)
app.config['SECRET_KEY'] = "secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
db.init_app(app)
migrate = Migrate(app, db)
app_login = LoginManager(app)
app_login.login_view = 'log.login'
app_login.login_message = _('Please log in to access this page.')
app_login.login_message_category = 'info'
babel = Babel(app)
try:
    oauth.init_app(app)
except NameError:
    pass

if not os.path.exists('instance/site.db'):
    with app.app_context():
        db.create_all()

if not os.path.exists('static/uploads'):
    os.makedirs('static/uploads')
if not os.path.exists('static/profile_pics'):
    os.makedirs('static/profile_pics')

app.register_blueprint(admin_bp)
try:
    app.register_blueprint(discord_bp)
except (NameError, ImportError, RuntimeError, LookupError):
    pass
app.register_blueprint(post_bp)
app.register_blueprint(log_bp)
app.register_blueprint(support_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(like_bp)
app.register_blueprint(user_bp)
app.register_blueprint(friends_bp)
app.register_blueprint(noti_bp)
app.register_blueprint(credits_bp)

with app.app_context():
    if db.session.query(ShopItem).count() == 0:
        db.session.add(ShopItem(
            name="Premium Account",
            description="Exclusive features and content.",
            price=100,
            icon="bi-star"
        ))
        db.session.add(ShopItem(
            name="Gold Profile Frame",
            description="Adds a golden profile frame to your profile.",
            price=50,
            icon="bi-person-bounding-box"
        ))
        db.session.add(ShopItem(
            name="Extra Upload Slot",
            description="Become able to upload more files.",
            price=130,
            icon="bi-cloud-upload"
        ))
        db.session.add(ShopItem(
            name="More Types",
            description="More types for your posts. Limit: 500 types per post.",
            price=80,
            icon="bi-megaphone"
        ))
        db.session.commit()
    else:
        pass

def get_locale():
    lang = request.cookies.get('lang')
    if lang in ['de', 'en']:
        return lang

babel.init_app(app, locale_selector=get_locale)

def needs_admin_setup():
    return db.session.query(User).filter_by(is_admin=True).count() == 0

@app.context_processor
def inject_discord_available():
    try:
        from routes.oauth import discord
        return dict(discord=discord)
    except ImportError:
        return dict(discord=None)

@app.context_processor
def inject_user():
    return dict(user=current_user if current_user.is_authenticated else None)

@app.context_processor
def inject_theme():
    theme = request.cookies.get('theme')
    if not theme:
        theme = 'dark'
    return dict(theme_class=f"{theme}-mode" if theme else "")

@app.context_processor
def inject_locale():
    return dict(get_locale=get_locale)

@app.context_processor
def inject_shopitem_ids():
    return dict(
        SHOPITEM_ID_GOLDRAHMEN=SHOPITEM_ID_GOLDRAHMEN,
        SHOPITEM_ID_PREMIUM=SHOPITEM_ID_PREMIUM,
        SHOPITEM_ID_EXTRA_UPLOAD=SHOPITEM_ID_EXTRA_UPLOAD,
        SHOPITEM_ID_EXTRA_TYPES=SHOPITEM_ID_EXTRA_TYPES
    )

@app_login.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.before_request
def check_for_admin():
    allowed_routes = ['setup', 'static']
    if needs_admin_setup() and request.endpoint not in allowed_routes:
        return redirect(url_for('setup'))

@app.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('post.feed'))
    return render_template('index.html')


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if not needs_admin_setup():
        return redirect(url_for('log.login'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash(_('Passwords do not match.'), 'danger')
        elif db.session.query(User).filter_by(username=username).first():
            flash(_('Username already exists.'), 'danger')
        elif db.session.query(User).filter_by(email=email).first():
            flash(_('E-Mail already exists.'), 'danger')
        elif len(password) < 8:
            flash(_('Password must be at least 8 characters long.'), 'danger')
        elif not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            flash(_('Invalid email address.'), 'danger')
        elif not re.match(r'^[a-zA-Z0-9_.+-]+$', username):
            flash(_('Invalid username. Only alphanumeric characters are allowed.'), 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            admin_user = User(username=username, email=email, password=hashed_password, is_admin=True, is_owner=True)
            db.session.add(admin_user)
            db.session.commit()
            flash(_('Admin account created. You can now log in.'), 'success')
            return redirect(url_for('log.login'))
    return render_template('setup.html')

@app.route('/shop', methods=['GET', 'POST'])
@login_required
def shop():
    items = db.session.query(ShopItem).all()
    message = None
    owned_ids = [usi.item_id for usi in current_user.shop_items]
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        item = db.session.get(ShopItem, item_id)
        if item_id in owned_ids:
            message = _("Already purchased!")
        elif item and current_user.reward_points() >= item.price:
            db.session.add(Reward(user_id=current_user.id, type=f'buy_{item.name}', points=-item.price))
            db.session.add(UserShopItem(user_id=current_user.id, item_id=item.id))
            db.session.commit()
            message = _(f"Purchased: {item.name}")
            owned_ids.append(item_id)
        else:
            message = _("Not enough points!")
    return render_template('shop.html', items=items, message=message, owned_ids=owned_ids)

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(error):
    flash(f'{error}', 'danger')
    if current_user.is_authenticated:
        return redirect(url_for('post.feed'))
    return render_template('index.html'), 200

if __name__ == '__main__':
    try:
        serve(app, host="0.0.0.0", port=80, threads=12)
    except:
        app.run(debug=True, host="0.0.0.0", port=80)
