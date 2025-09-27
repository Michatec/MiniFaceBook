from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from models import db, User, Post, Friendship, Comment, Upload, Notification, Event, PasswordResetRequest, Like, UserShopItem, Reward, SupportComment, SupportRequest
from werkzeug.security import generate_password_hash
from flask_babel import gettext as _
import os

__mapper_args__ = {"confirm_deleted_rows": False}
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/reset_requests/delete_all', methods=['GET', 'POST'])
@login_required
def admin_delete_all_reset_requests():
    if not current_user.is_admin:
        abort(403)
    db.session.query(PasswordResetRequest).delete()
    db.session.commit()
    flash(_('All password reset requests have been deleted.'), 'success')
    return redirect(url_for('admin.reset_requests'))

@admin_bp.route('/')
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)
    users = db.session.query(User).all()
    posts = db.session.query(Post).all()
    friendships = db.session.query(Friendship).all()
    comments = db.session.query(Comment).all()
    uploads = db.session.query(Upload).all()
    all_notifications = db.session.query(Notification).order_by(Notification.created_at.desc()).all()
    events = db.session.query(Event).order_by(Event.timestamp.desc()).limit(50).all()
    user_shop_items = db.session.query(UserShopItem).all()
    return render_template(
        'admin.html',
        users=users,
        posts=posts,
        friendships=friendships,
        comments=comments,
        uploads=uploads,
        all_notifications=all_notifications,
        events=events,
        user_shop_items=user_shop_items
    )

@admin_bp.route('/reset_requests')
@login_required
def reset_requests():
    if not current_user.is_admin:
        abort(403)
    requests = db.session.query(PasswordResetRequest).filter_by(status='pending').all()
    requests_done = db.session.query(PasswordResetRequest).filter_by(status='done').all()
    requests_rejected = db.session.query(PasswordResetRequest).filter_by(status='rejected').all()
    return render_template('reset_requests.html', requests=requests, requests_done=requests_done, requests_rejected=requests_rejected)

@admin_bp.route('/reset_requests/<int:req_id>/reject', methods=['POST'])
@login_required
def reject_reset_request(req_id):
    if not current_user.is_admin:
        abort(403)
    req = db.session.get(PasswordResetRequest, req_id)
    if req:
        req.status = 'rejected'
        db.session.commit()
        flash(_('Request rejected.'), 'info')
    return redirect(url_for('admin.reset_requests'))

@admin_bp.route('/reset_requests/<int:req_id>/reset', methods=['GET', 'POST'])
@login_required
def admin_reset_password(req_id):
    if not current_user.is_admin:
        abort(403)
    req = db.session.get(PasswordResetRequest, req_id)
    if req and req.status == 'pending':
        user = db.session.get(User, req.user_id)
        if request.method == 'POST':
            new_pw = request.form['new_password']
            if not new_pw or len(new_pw) < 4:
                flash(_('Password too short.'), 'danger')
            else:
                user.password = generate_password_hash(new_pw, method='pbkdf2:sha256')
                req.status = 'done'
                db.session.commit()
                flash(_(f'Password for {user.username} reset.'), 'success')
                return redirect(url_for('admin.reset_requests'))
        return render_template('admin_set_password.html', req=req, user=user)
    return redirect(url_for('admin.reset_requests'))

@admin_bp.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    if not current_user.is_admin:
        abort(403)
    post = db.session.get(Post, post_id)
    if post:
        for upload in post.uploads:
            file_path = os.path.join('static/uploads', upload.filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        likes = db.session.query(Like).filter_by(post_id=post_id).all()
        for like in likes:
            db.session.delete(like)
        comments = db.session.query(Comment).filter_by(post_id=post_id).all()
        for comment in comments:
            db.session.delete(comment)
        db.session.delete(post)
        event = Event(message=_(f"Admin {current_user.username} has deleted post {post.id}."))
        db.session.add(event)
        notification = Notification(message=_(f"Your post {post.id} has been deleted by an admin."), user_id=post.user_id)
        db.session.add(notification)
        db.session.commit()
        flash(_('Post and associated files deleted.'), 'success')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    user = db.session.get(User, user_id)
    if user.is_owner:
        flash(_('Cannot delete the owner account.'), 'danger')
        return redirect(url_for('admin.admin')) 
    if user and not user.is_admin:
        event = Event(message=f"Admin {current_user.username} hat {user.username} gelöscht.")
        db.session.add(event)
        for post in user.posts:
            db.session.delete(post)
        for friendship in user.friendships_sent + user.friendships_received:
            db.session.delete(friendship)
        for comment in user.comments:
            db.session.delete(comment)
        for user_shop_item in user.shop_items:
            db.session.delete(user_shop_item)
        for reward in user.rewards:
            db.session.delete(reward)
        for like in user.likes:
            db.session.delete(like)
        for upload in user.uploads:
            file_path = os.path.join('static/uploads', upload.filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            db.session.delete(upload)
        if user.profile_pic and not user.profile_pic == 'default.png':
            try:
                os.remove(os.path.join('static/profile_pics', user.profile_pic))
            except Exception:
                pass
        notifications = db.session.query(Notification).filter_by(user_id=user.id).all()
        for notif in notifications:
            db.session.delete(notif)
        db.session.delete(user)
        db.session.commit()
        flash(_('User deleted.'), 'success')
    else:
        flash(_('Cannot delete admin or user not found.'), 'danger')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/delete_pic/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_pic(user_id):
    if not current_user.is_admin:
        abort(403)
    user = db.session.get(User, user_id)
    if user and user.profile_pic and user.profile_pic != 'default.png':
        try:
            os.remove(os.path.join('static/profile_pics', user.profile_pic))
        except Exception:
            pass
        user.profile_pic = "default.png"
        db.session.commit()
        flash(_(f'Profile picture of {user.username} deleted.'), 'success')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/delete_all_notifications', methods=['POST'])
@login_required
def admin_delete_all_notifications():
    if not current_user.is_admin:
        abort(403)
    db.session.query(Notification).delete()
    db.session.commit()
    flash(_('All notifications have been deleted.'), 'success')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/delete_all_events', methods=['POST'])
@login_required
def admin_delete_all_events():
    if not current_user.is_admin:
        abort(403)
    db.session.query(Event).delete()
    db.session.commit()
    flash(_('All events have been deleted.'), 'success')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/delete_upload/<int:upload_id>', methods=['POST'])
@login_required
def admin_delete_upload(upload_id):
    if not current_user.is_admin:
        abort(403)
    upload = db.session.get(Upload, upload_id)
    if upload:
        file_path = os.path.join('static/uploads', upload.filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        db.session.delete(upload)
        db.session.commit()
        flash(_('Upload deleted.'), 'success')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/delete_all_uploads', methods=['POST'])
@login_required
def admin_delete_all_uploads():
    if not current_user.is_admin:
        abort(403)
    db.session.query(Upload).delete()
    db.session.commit()
    upload_dir = 'static/uploads'
    for filename in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception:
            pass
    flash(_('All uploads have been deleted.'), 'success')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/admin/points/<int:user_id>', methods=['POST'])
@login_required
def admin_points(user_id):
    if not current_user.is_admin:
        abort(403)
    action = request.form.get('action')
    try:
        points = int(request.form['points'])
    except:
        flash(_('No Points entered!'))
        return redirect(url_for('admin.admin'))
    cuser = db.session.get(User, current_user.id)
    if not cuser.is_owner:
        abort(403)
    if action == 'add':
        db.session.add(Reward(user_id=user_id, type='admin', points=points))
        db.session.commit()
        flash(_('Points added!'), 'success')
    elif action == 'remove':
        user = db.session.get(User, user_id)
        if user.reward_points() >= points:
            db.session.add(Reward(user_id=user_id, type='admin', points=-points))
            db.session.commit()
            flash(_('Points removed!'), 'success')
        else:
            flash(_("The user has not enough points to take!"), 'danger')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/make_admin/<int:user_id>', methods=['POST'])
@login_required
def make_admin(user_id):
    if not current_user.is_admin:
        abort(403)
    user = db.session.get(User, user_id)
    if user and not user.is_admin:
        user.is_admin = True
        db.session.commit()
        flash(_(f"{user.username} is now an admin."), "success")
    return redirect(url_for('admin.admin'))

@admin_bp.route('/remove_admin/<int:user_id>', methods=['POST'])
@login_required
def remove_admin(user_id):
    if not current_user.is_admin:
        abort(403)
    user = db.session.get(User, user_id)
    if user and user.is_admin and not user.is_owner:
        user.is_admin = False
        db.session.commit()
        flash(_(f"Admin rights of {user.username} removed."), "info")
    else:
        flash(_("Owner cannot be removed!"), "danger")
    return redirect(url_for('admin.admin'))

@admin_bp.route('/wipe_server', methods=['POST'])
@login_required
def wipe_server():
    if not current_user.is_admin and not current_user.is_owner:
        abort(403)

    db.session.query(Reward).delete()
    db.session.query(UserShopItem).delete()
    db.session.query(Like).delete()
    db.session.query(Comment).delete()
    db.session.query(Friendship).delete()
    db.session.query(Post).delete()
    db.session.query(Upload).delete()
    db.session.query(Notification).delete()
    db.session.query(Event).delete()
    db.session.query(PasswordResetRequest).delete()
    db.session.query(User).delete()
    db.session.query(SupportComment).delete()
    db.session.query(SupportRequest).delete()
    db.session.commit()

    upload_dir = 'static/uploads'
    for filename in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception:
            pass

    profile_dir = 'static/profile_pics'
    for filename in os.listdir(profile_dir):
        if filename != 'default.png':
            file_path = os.path.join(profile_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    flash(_('All Data has been deleted.'), 'success')
    return redirect(url_for('admin.admin'))