from flask import Blueprint, redirect, url_for, flash, request, render_template
from flask_login import logout_user
from flask_login import login_required, current_user
from models import db, Notification, Upload, Event, User
from flask_babel import gettext as _
import os
from datetime import datetime

__mapper_args__ = {"confirm_deleted_rows": False}
user_bp = Blueprint('user', __name__)

@user_bp.route('/delete_pic', methods=['POST'])
@login_required
def delete_pic():
    if current_user.profile_pic and current_user.profile_pic != 'default.png':
        try:
            os.remove(os.path.join('static/profile_pics', current_user.profile_pic))
        except Exception:
            pass
        current_user.profile_pic = 'default.png'
        db.session.commit()
        flash(_('Profile picture deleted.'), 'success')
    return redirect(url_for('profil.profile'))

@user_bp.route('/upload_pic', methods=['POST'])
@login_required
def upload_pic():
    file = request.files['profile_pic']
    if file:
        if current_user.profile_pic and current_user.profile_pic != 'default.png':
            try:
                os.remove(os.path.join('static/profile_pics', current_user.profile_pic))
            except Exception:
                pass
            current_user.profile_pic = 'default.png'
            db.session.commit()

        ext = os.path.splitext(file.filename)[1]
        filename = f"user_{current_user.id}_{int(datetime.now().timestamp())}{ext}"
        filepath = os.path.join('static/profile_pics', filename)
        file.save(filepath)
        current_user.profile_pic = filename
        db.session.commit()

        notif = Notification(user_id=current_user.id, message=_("You have changed your profile picture."))
        db.session.add(notif)
        db.session.commit()

        event = Event(message=_(f"{current_user.username} has changed their profile picture."))
        db.session.add(event)
        db.session.commit()
        flash(_('Profile picture updated.'), 'success')
    return redirect(url_for('profil.profile'))

@user_bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    if current_user.is_owner:
        flash(_('You cannot delete the owner account.'), 'danger')
        return redirect(url_for('profil.profile'))
    if current_user.is_admin:
        flash(_('You cannot delete an admin account.'), 'danger')
        return redirect(url_for('profil.profile'))
    event = Event(message=f"{current_user.username} hat sein Konto gelöscht.")
    db.session.add(event)
    for post in current_user.posts:
        db.session.delete(post)
    for friendship in current_user.friendships_sent + current_user.friendships_received:
        db.session.delete(friendship)
    for comment in current_user.comments:
        db.session.delete(comment)
    for like in current_user.likes:
        db.session.delete(like)
    for shop_item in current_user.shop_items:
        db.session.delete(shop_item)
    for reward in current_user.rewards:
        db.session.delete(reward)
    for upload in current_user.uploads:
        file_path = os.path.join('static/uploads', upload.filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        db.session.delete(upload)
    if current_user.profile_pic and not current_user.profile_pic == 'default.png':
        try:
            os.remove(os.path.join('static/profile_pics', current_user.profile_pic))
        except Exception:
            pass
    notifications = db.session.query(Notification).filter_by(user_id=current_user.id).all()
    for notif in notifications:
        db.session.delete(notif)
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash(_('Account and all your data deleted.'), 'success')
    return redirect(url_for('index'))

@user_bp.route('/users')
@login_required
def users():
    all_users = db.session.query(User).filter(User.id != current_user.id).all()
    return render_template('users.html', users=all_users)