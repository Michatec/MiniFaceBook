from flask import Blueprint, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from models import db, Notification
from flask_babel import gettext as _
from datetime import datetime, timedelta

noti_bp = Blueprint('notif', __name__)

@noti_bp.route('/delete_all_notifications', methods=['POST'])
@login_required
def delete_all_notifications():
    db.session.query(Notification).filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash(_('All notifications have been deleted.'), 'success')
    return redirect(url_for('notif.notifications'))

@noti_bp.route('/delete_notification/<int:notif_id>', methods=['POST'])
@login_required
def delete_notification(notif_id):
    notif = db.session.get(Notification, notif_id)
    if notif and notif.user_id == current_user.id:
        db.session.delete(notif)
        db.session.commit()
    return redirect(url_for('notif.notifications'))

@noti_bp.route('/notifications')
@login_required
def notifications():
    expire_time = datetime.now() - timedelta(days=3)
    db.session.query(Notification).filter(Notification.created_at < expire_time).delete()
    db.session.commit()
    notifications = db.session.query(Notification).filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)