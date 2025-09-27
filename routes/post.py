from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Post, Reward, Friendship, Upload, Notification, Event, SHOPITEM_ID_EXTRA_UPLOAD, SHOPITEM_ID_EXTRA_TYPES, Like, Comment
from flask_babel import gettext as _
from sqlalchemy import func
from datetime import datetime, date
import os

post_bp = Blueprint('post', __name__)

@post_bp.route('/post', methods=['POST'])
@login_required
def create_post():
    content = request.form['content']
    visibility = request.form.get('visibility', 'public') 
    file = request.files.get('file')
    file2 = request.files.get('file2')
    post = None
    if content:
        post = Post(user_id=current_user.id, content=content, visibility=visibility)
        if not SHOPITEM_ID_EXTRA_TYPES in [usi.item_id for usi in current_user.shop_items]:
            if len(content) > 250:
                flash(_('Post content is too long. Please limit it to 250 characters.'), 'danger')
                return redirect(url_for('post.feed'))
        else:
            if len(content) > 500:
                flash(_('Post content is too long. Please limit it to 500 characters.'), 'danger')
                return redirect(url_for('post.feed'))
        db.session.add(post)
        db.session.commit()
        flash(_('Post created!'), 'success')
        if file and file.filename:
            ext = os.path.splitext(file.filename)[1]
            filename = f"user_{current_user.id}_{int(datetime.now().timestamp())}{ext}"
            filepath = os.path.join('static/uploads', filename)
            file.save(filepath)
            upload = Upload(user_id=current_user.id, post_id=post.id, filename=filename, filetype=file.content_type)
            db.session.add(upload)
            db.session.commit()
        if file2 and file2.filename and SHOPITEM_ID_EXTRA_UPLOAD in [usi.item_id for usi in current_user.shop_items]:
            ext = os.path.splitext(file2.filename)[1]
            filename = f"user_{current_user.id}_{int(datetime.now().timestamp())}_extra{ext}"
            filepath = os.path.join('static/uploads', filename)
            file2.save(filepath)
            upload2 = Upload(user_id=current_user.id, post_id=post.id, filename=filename, filetype=file2.content_type)
            db.session.add(upload2)
            db.session.commit()
    event = Event(message=_(f"{current_user.username} has created a new post."))
    db.session.add(event)
    db.session.commit()
    notif = Notification(user_id=current_user.id, message=_("You have created a new post."))
    db.session.add(notif)
    db.session.add(Reward(user_id=current_user.id, type='post', points=5))
    db.session.commit()

    return redirect(url_for('post.feed'))

@post_bp.route('/edit_post/<int:post_id>', methods=['GET'])
@login_required
def edit_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash(_('Post does not exist.'), 'danger')
        return redirect(url_for('post.feed'))
    if post.user_id != current_user.id:
        flash(_('You do not have permission to edit this post.'), 'danger')
        return redirect(url_for('post.feed'))
    return render_template('edit_post.html', post=post)

@post_bp.route('/update_post/<int:post_id>', methods=['POST', 'GET'])
@login_required
def update_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash(_('Post does not exist.'), 'danger')
        return redirect(url_for('post.feed'))
    if post.user_id != current_user.id:
        flash(_('You do not have permission to edit this post.'), 'danger')
        return redirect(url_for('post.feed'))
    content = request.form['content']
    visibility = request.form.get('visibility', 'public')
    post.content = content
    post.visibility = visibility
    file = request.files.get('upload')
    file2 = request.files.get('upload2')
    if not SHOPITEM_ID_EXTRA_TYPES in [usi.item_id for usi in current_user.shop_items]:
        if len(post.content) > 250:
            flash(_('Post content is too long. Please limit it to 250 characters.'), 'danger')
            return redirect(url_for('post.feed'))
    else:
        if len(post.content) > 500:
            flash(_('Post content is too long. Please limit it to 500 characters.'), 'danger')
            return redirect(url_for('post.feed'))
    
    if file:
        for upload in post.uploads:
            file_path = os.path.join('static/uploads', upload.filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            
            db.session.delete(upload)

        ext = os.path.splitext(file.filename)[1]
        filename = f"user_{current_user.id}_{int(datetime.now().timestamp())}{ext}"
        filepath = os.path.join('static/uploads', filename)
        file.save(filepath)
        upload = Upload(user_id=current_user.id, post_id=post.id, filename=filename, filetype=file.content_type)
        db.session.add(upload)

    if file2 and SHOPITEM_ID_EXTRA_UPLOAD in [usi.item_id for usi in current_user.shop_items]:
        for upload in post.uploads:
            if upload.filename.endswith('_extra' + os.path.splitext(file2.filename)[1]):
                file_path = os.path.join('static/uploads', upload.filename)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                
                db.session.delete(upload)

        ext = os.path.splitext(file2.filename)[1]
        filename = f"user_{current_user.id}_{int(datetime.now().timestamp())}_extra{ext}"
        filepath = os.path.join('static/uploads', filename)
        file2.save(filepath)
        upload2 = Upload(user_id=current_user.id, post_id=post.id, filename=filename, filetype=file2.content_type)
        db.session.add(upload2)

    notif = Notification(user_id=current_user.id, message=_("Your post has been updated."))
    db.session.add(notif)
    event = Event(message=f"{current_user.username} has updated post {post.id}.")
    db.session.add(event)
    db.session.commit()
    flash(_('Post updated!'), 'success')
    return redirect(url_for('post.feed'))

@post_bp.route('/feed')
def feed():
    if current_user.is_authenticated:
        today = date.today()
        reward_today = db.session.query(Reward).filter(
            Reward.user_id == current_user.id,
            Reward.type == 'daily',
            func.date(Reward.created_at) == today
        ).first()

        if not reward_today:
            db.session.add(Reward(user_id=current_user.id, type='daily', points=10))
            db.session.commit()
        
        if current_user.is_admin:
            posts = db.session.query(Post).order_by(Post.created_at.desc()).all()
        else:
            friend_ids = [
                f.requester_id if f.requester_id != current_user.id else f.receiver_id
                for f in db.session.query(Friendship).filter(
                    ((Friendship.requester_id == current_user.id) | (Friendship.receiver_id == current_user.id)),
                    Friendship.status == 'accepted'
                ).all()
            ]
            posts = db.session.query(Post).filter(
                (Post.visibility == 'public') |
                ((Post.visibility == 'friends') & (Post.user_id.in_(friend_ids + [current_user.id])))
            ).order_by(Post.created_at.desc()).all()
    else:
        posts = db.session.query(Post).filter_by(visibility='public').order_by(Post.created_at.desc()).all()
    events = db.session.query(Event).order_by(Event.timestamp.desc()).limit(20).all()
    return render_template('feed.html', posts=posts, events=events)

@post_bp.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if post and post.user_id == current_user.id:
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
        db.session.delete(post)
        comments = db.session.query(Comment).filter_by(post_id=post_id).all()
        for comment in comments:
            db.session.delete(comment)
        notif = Notification(user_id=current_user.id, message=_("Your post has been deleted."))
        db.session.add(notif)
        event = Event(message=_(f"{current_user.username} has deleted post {post.id}."))
        db.session.add(event)
        db.session.commit()
        flash(_('Post and all uploads deleted.'), 'success')
    else:
        flash(_('Not allowed.'), 'danger')
    return redirect(url_for('post.feed'))

@post_bp.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment and comment.user_id == current_user.id:
        db.session.delete(comment)
        db.session.commit()
        flash(_('Comment deleted.'), 'success')
    else:
        flash(_('Not allowed.'), 'danger')
    return redirect(url_for('post.feed'))

@post_bp.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment_post(post_id):
    content = request.form['comment']
    if content:
        comment = Comment(post_id=post_id, user_id=current_user.id, content=content)
        db.session.add(comment)
        notif = Notification(user_id=current_user.id, message=_("You have written a comment."))
        db.session.add(notif)
        db.session.add(Reward(user_id=current_user.id, type='comment', points=2))
        db.session.commit()
    return redirect(url_for('post.feed'))