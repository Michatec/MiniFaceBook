from flask import Blueprint, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from models import db, Notification, Event, User, Friendship, Reward
from flask_babel import gettext as _

friends_bp = Blueprint('friend', __name__)

@friends_bp.route('/add_friend/<int:user_id>', methods=['POST'])
@login_required
def add_friend(user_id):
    if user_id == current_user.id:
        flash(_('You cannot add yourself as a friend.'), 'warning')
        return redirect(url_for('user.users'))
    existing = db.session.query(Friendship).filter_by(requester_id=current_user.id, receiver_id=user_id).first()
    if existing:
        flash(_('Friend request already sent.'), 'info')
    else:
        friendship = Friendship(requester_id=current_user.id, receiver_id=user_id)
        db.session.add(friendship)
        db.session.commit()
        friend = db.session.get(User, user_id)
        event = Event(message=_(f"{current_user.username} sent a friend request to {friend.username}."))
        db.session.add(event)
        db.session.commit()
        notif = Notification(
            user_id=user_id,
            message=_(f"You have received a friend request from {current_user.username}.")
        )
        db.session.add(notif)
        db.session.commit()
        flash(_('Friend request sent!'), 'success')
    return redirect(url_for('user.users'))

@friends_bp.route('/accept_friend/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend(friendship_id):
    friendship = db.session.get(Friendship, friendship_id)
    if friendship and friendship.receiver_id == current_user.id:
        friendship.status = 'accepted'
        db.session.commit()
        friend = db.session.get(User, friendship.requester_id)
        event = Event(message=_(f"{current_user.username} und {friend.username} sind jetzt Freunde."))
        db.session.add(event)
        db.session.add(Reward(user_id=current_user.id, type='friendship', points=5))
        db.session.add(Reward(user_id=friendship.requester_id, type='friendship', points=5))
        db.session.commit()
        flash(_('Friend request accepted!'), 'success')
    else:
        flash(_('Invalid friend request.'), 'danger')
    return redirect(url_for('friend.friends'))

@friends_bp.route('/reject_friend/<int:friendship_id>', methods=['POST'])
@login_required
def reject_friend(friendship_id):
    friendship = db.session.get(Friendship, friendship_id)
    if friendship and friendship.receiver_id == current_user.id:
        friendship.status = 'rejected'
        db.session.commit()
        friend = db.session.get(User, friendship.requester_id)
        event = Event(message=_(f"{current_user.username} has rejected {friend.username}'s friend request."))
        db.session.add(event)
        db.session.commit()
        flash(_('Friend request rejected.'), 'info')
    else:
        flash(_('Invalid friend request.'), 'danger')
    return redirect(url_for('friend.friends'))

@friends_bp.route('/friends')
@login_required
def friends():
    friends = db.session.query(User).join(Friendship, ((Friendship.requester_id == User.id) | (Friendship.receiver_id == User.id)))\
        .filter(
            ((Friendship.requester_id == current_user.id) | (Friendship.receiver_id == current_user.id)),
            Friendship.status == 'accepted',
            User.id != current_user.id
        ).all()
    requests = db.session.query(Friendship).filter_by(receiver_id=current_user.id, status='pending').all()
    return render_template('friends.html', friends=friends, requests=requests)

@friends_bp.route('/remove_friend/<int:user_id>', methods=['POST'])
@login_required
def remove_friend(user_id):
    friendship = db.session.query(Friendship).filter(
        ((Friendship.requester_id == current_user.id) & (Friendship.receiver_id == user_id)) |
        ((Friendship.requester_id == user_id) & (Friendship.receiver_id == current_user.id)),
        Friendship.status == 'accepted'
    ).first()
    if friendship:
        db.session.delete(friendship)
        db.session.commit()
        flash(_('Friendship ended.'), 'info')
    return redirect(url_for('friend.friends'))