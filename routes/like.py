from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Post, Notification, Like
from flask_babel import gettext as _

like_bp = Blueprint('like', __name__)

@like_bp.route('/like/<int:post_id>', methods=['POST', 'GET'])
@login_required
def like_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash(_('Post does not exist.'), 'danger')
        return redirect(url_for('post.feed'))
    like = db.session.query(Like).filter_by(post_id=post_id, user_id=current_user.id).first()
    if not like:
        db.session.add(Like(post_id=post_id, user_id=current_user.id))
        db.session.commit()
        if post.user_id != current_user.id:
            notif = Notification(
                user_id=post.user_id,
                message=_(f"{current_user.username} liked your post.")
            )
            db.session.add(notif)
            db.session.commit()
        flash(_('Post liked.'), 'info')
    return redirect(url_for('post.feed'))

@like_bp.route('/unlike/<int:post_id>', methods=['POST', 'GET'])
@login_required
def unlike_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash(_('Post does not exist.'), 'danger')
        return redirect(url_for('post.feed'))
    like = db.session.query(Like).filter_by(post_id=post_id, user_id=current_user.id).first()
    if like:
        db.session.delete(like)
        db.session.commit()
        flash(_('Like removed.'), 'info')
    return redirect(url_for('post.feed'))