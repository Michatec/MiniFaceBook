from flask import Flask, request, render_template, redirect, url_for, flash, abort, jsonify, current_app, session, has_request_context
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
from dotenv import load_dotenv
import logging
import re
import os, sys

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

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

def get_locale():
    if has_request_context():
        lang = request.cookies.get('lang')
        if lang in ['de', 'en']:
            return lang
    return None

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
    if 'shop_csrf_token' not in session:
        session['shop_csrf_token'] = os.urandom(24).hex()
    csrf_token_value = session['shop_csrf_token']
    
    items = db.session.query(ShopItem).order_by(ShopItem.price.asc()).all()
    owned_ids = [usi.item_id for usi in current_user.shop_items]
    user_points = current_user.reward_points()
    
    if request.method == 'POST':
        if request.form.get('csrf_token') != session.get('shop_csrf_token'):
            logger.warning(f"CSRF token mismatch for user {current_user.id} in shop")
            abort(403)
        
        try:
            item_id = int(request.form['item_id'])
        except (ValueError, TypeError):
            flash(_('Invalid item selected.'), 'danger')
            return redirect(url_for('shop'))
        
        item = db.session.get(ShopItem, item_id)
        
        if not item:
            flash(_('Item not found.'), 'danger')
        elif item_id in owned_ids:
            flash(_('Already purchased!'), 'warning')
        elif user_points < item.price:
            flash(_('Not enough points! You need %(needed)d more.', needed=item.price - user_points), 'danger')
        else:
            try:
                db.session.add(Reward(user_id=current_user.id, type=f'buy_{item.name}', points=-item.price))
                db.session.add(UserShopItem(user_id=current_user.id, item_id=item.id))
                db.session.commit()
                session['shop_csrf_token'] = os.urandom(24).hex()
                flash(_('Successfully purchased: %(item_name)s', item_name=item.name), 'success')
                return redirect(url_for('shop'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Shop purchase failed for user {current_user.id}: {e}")
                flash(_('Purchase failed. Please try again.'), 'danger')
    
    return render_template('shop.html', items=items, owned_ids=owned_ids, 
                           user_points=user_points, csrf_token_value=csrf_token_value)

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(error):
    flash(f'{error}', 'danger')
    if current_user.is_authenticated:
        return redirect(url_for('post.feed'))
    return render_template('index.html'), 200

def print_error(message):
    print(f"\033[91m[ERROR] {message}\033[0m")

def print_loading(message):
    colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]
    color = colors[hash(message) % len(colors)]
    print(f"{color}◆ {message}...\033[0m")


def print_success(message):
    colors = ["\033[92m", "\033[96m", "\033[94m", "\033[95m"]
    color = colors[hash(message) % len(colors)]
    print(f"{color}✓ {message}\033[0m")

def print_rainbow_separator():
    rainbow = "\033[91m▆\033[93m▆\033[92m▆\033[96m▆\033[94m▆\033[95m▆\033[0m"
    print(f"  {rainbow * 12}")

if __name__ == '__main__':
    print_loading("Starting MiniFaceBook...")
    print_rainbow_separator()
    print_loading("Initializing database")
    try:
        with app.app_context():
            if db.session.query(ShopItem).count() == 0:
                shop_items = [
                     {
                          'name': _('Premium Account'),
                          'description': _('Exclusive features and content.'),
                          'price': 100,
                          'icon': 'bi-star'
                     },
                     {
                          'name': _('Gold Profile Frame'),
                          'description': _('Adds a golden profile frame to your profile.'),
                          'price': 50,
                          'icon': 'bi-person-bounding-box'
                     },
                     {
                          'name': _('Extra Upload Slot'),
                          'description': _('Become able to upload more files.'),
                          'price': 130,
                          'icon': 'bi-cloud-upload'
                     },
                     {
                          'name': _('More Types'),
                          'description': _('More types for your posts. Limit: 500 types per post.'),
                          'price': 80,
                          'icon': 'bi-megaphone'
                     }
                ]
                
                for item_data in shop_items:
                    item = ShopItem(**item_data)
                    db.session.add(item)
                db.session.commit()
        print_success("Database initialized successfully.")
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        print_error("Please check your database configuration and ensure the database is accessible.")
        sys.exit(1)
    
    print_loading("Loading environment variables")
    try:
        load_dotenv()
        port = os.environ.get('PORT')
        print_success("Environment variables loaded successfully.")
    except Exception as e:
        print_error(f"Failed to load environment variables: {e}")
        print_error("Please set the environment variables!")
        sys.exit(1)
        
    print_loading(f"Using port {port}")
    print_rainbow_separator()
    print_loading("Starting server with Waitress")
    
    try:
        print_success(f"Server started successfully with Waitress at the port {port}.")
        serve(app, host="0.0.0.0", port=port, threads=12, connection_limit=1000)
    except:
        print_error(f"Failed to start with Waitress, falling back to Flask's built-in server at port {port}. This is not recommended for production use.")
        app.run(debug=True, host="0.0.0.0", port=port)