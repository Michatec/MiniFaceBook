from flask import Blueprint, jsonify, redirect, request, url_for, flash, render_template, abort
from flask_login import login_required, current_user
from models import User, db, Notification, Event
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

@noti_bp.route('/api/notifications')
@login_required
def notifications_api():
    expire_time = datetime.now() - timedelta(days=3)
    db.session.query(Notification).filter(Notification.created_at < expire_time).delete()
    db.session.commit()
    notifications = db.session.query(Notification).filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify(
        [
            {
                'name': User.query.get(n.user_id).username,
                'data': n.message,
                'created_at': n.created_at
            } for n in notifications
        ]
    )

@noti_bp.route('/api/events')
@login_required
def api_events():
    if not current_user.is_admin:
        abort(403)

    events = db.session.query(Event).order_by(Event.timestamp.desc()).limit(20).all()
    return jsonify([
        {"timestamp": e.timestamp.strftime('%Y-%m-%d %H:%M'), "message": e.message}
        for e in events
    ])