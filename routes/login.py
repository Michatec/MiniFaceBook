from flask import Blueprint, render_template, redirect, url_for, flash, request
from models import db, User, PasswordResetRequest
from flask_babel import gettext as _
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re

log_bp = Blueprint('log', __name__)

@log_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('post.feed'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(_('Logged in successfully.'), 'success')
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for('post.feed'))
        else:
            flash(_('Invalid username or password.'), 'danger')
    return render_template('login.html')

@log_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('Logged out successfully.'), 'success')
    return redirect(url_for('index'))

@log_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('post.feed'))
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
        elif len(username) < 3 or len(username) > 20:
            flash(_('Username must be between 3 and 20 characters long.'), 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash(_('Registered successfully. You can now log in.'), 'success')
            return redirect(url_for('log.login'))
    return render_template('register.html')

@log_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form['username']
        user = db.session.query(User).filter_by(username=username).first()
        if user:
            req = PasswordResetRequest(user_id=user.id)
            db.session.add(req)
            db.session.commit()
            flash(_('Reset request sent to admins.'), 'info')
        else:
            flash(_('No user with this email.'), 'danger')
    return render_template('reset_password.html')