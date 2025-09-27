from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Post
from flask_babel import gettext as _
from werkzeug.security import generate_password_hash
import re

profile_bp = Blueprint('profil', __name__)

@profile_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@profile_bp.route('/my_posts')
@login_required
def my_posts():
    posts = db.session.query(Post).filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('my_posts.html', posts=posts)

@profile_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        if not current_user.username or not current_user.email:
            flash(_('Username and email cannot be empty.'), 'danger')
            return redirect(url_for('profile.edit_profile'))
        else:
            if new_username and new_username != current_user.username:
                if db.session.query(User).filter_by(username=new_username).first():
                    flash(_('Username already taken.'), 'danger')
                    return redirect(url_for('profile.edit_profile'))
                elif not re.match(r'^[a-zA-Z0-9_.+-]+$', new_username):
                    flash(_('Invalid username. Only alphanumeric characters are allowed.'), 'danger')
                    return redirect(url_for('profile.edit_profile'))
                else:
                    current_user.username = new_username
            elif new_email and new_email != current_user.email:
                if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', new_email):
                    flash(_('Invalid email address.'), 'danger')
                    return redirect(url_for('profile.edit_profile'))
                elif db.session.query(User).filter_by(email=new_email).first():
                    flash(_('E-Mail already taken.'), 'danger')
                    return redirect(url_for('profile.edit_profile'))
                else:
                    current_user.email = new_email
            elif new_password:
                if len(new_password) < 8:
                    flash(_('Password must be at least 8 characters long.'), 'danger')
                    return redirect(url_for('profile.edit_profile'))
                elif new_password != confirm_password:
                    flash(_('Passwords do not match.'), 'danger')
                    return redirect(url_for('profile.edit_profile'))
                else:
                    current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            else:
                flash(_('No changes made.'), 'info')
                return redirect(url_for('profil.profile'))
            db.session.commit()
            flash(_('Profile updated.'), 'success')
            return redirect(url_for('profil.profile'))
    return render_template('edit_profile.html', user=current_user)