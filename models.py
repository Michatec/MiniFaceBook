from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from hashlib import md5

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_admin = db.Column(db.Boolean, default=False)
    is_owner = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(200), default='default.png')
    discord_id = db.Column(db.String(50), unique=True)
    discord_linked = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='user', cascade="all, delete", passive_deletes=True)
    comments = db.relationship('Comment', backref='user', cascade="all, delete", passive_deletes=True)
    likes = db.relationship('Like', backref='user', cascade="all, delete", passive_deletes=True)
    friendships_sent = db.relationship(
        'Friendship',
        foreign_keys='Friendship.requester_id',
        backref='requester',
        cascade="all, delete",
        passive_deletes=True
    )
    friendships_received = db.relationship(
        'Friendship',
        foreign_keys='Friendship.receiver_id',
        backref='receiver',
        cascade="all, delete",
        passive_deletes=True
    )
    uploads = db.relationship('Upload', backref='user', cascade="all, delete", passive_deletes=True)
    rewards = db.relationship('Reward', backref='user', cascade="all, delete", passive_deletes=True)
    shop_items = db.relationship('UserShopItem', backref='user', cascade="all, delete", passive_deletes=True)

    def reward_points(self):
        return sum(r.points for r in self.rewards)
    
    def avatar(self):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s=120'

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    visibility = db.Column(db.String(20), default='public')
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade="all, delete-orphan", passive_deletes=True)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", passive_deletes=True)
    uploads = db.relationship('Upload', backref='post', cascade="all, delete-orphan", passive_deletes=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class PasswordResetRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    requested_at = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='pending') 
    user = db.relationship('User', backref='reset_requests') 

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    filename = db.Column(db.String(255))
    filetype = db.Column(db.String(50))
    uploaded_at = db.Column(db.DateTime, default=datetime.now)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    message = db.Column(db.String(255))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    read = db.Column(db.Boolean, default=False)

class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

class ShopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    price = db.Column(db.Integer, nullable=False)
    icon = db.Column(db.String(50), default="bi-gift")

class UserShopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'))
    bought_at = db.Column(db.DateTime, default=datetime.now)
    item = db.relationship('ShopItem')

class SupportRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='open')
    comments = db.relationship('SupportComment', backref='request', cascade="all, delete", passive_deletes=True)

class SupportComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('support_request.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User')

SHOPITEM_ID_GOLDRAHMEN = 2
SHOPITEM_ID_PREMIUM = 1
SHOPITEM_ID_EXTRA_UPLOAD = 3
SHOPITEM_ID_EXTRA_TYPES = 4