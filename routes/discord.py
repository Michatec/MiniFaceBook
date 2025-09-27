from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User
from werkzeug.security import generate_password_hash
from flask_babel import gettext as _
from routes.oauth import discord
from routes.login import login_user

discord_bp = Blueprint('discord', __name__)

@discord_bp.route('/login/discord')
def login_discord():
    redirect_uri = url_for('discord.discord_login_callback', _external=True)
    return discord.authorize_redirect(redirect_uri)

@discord_bp.route('/login/discord/callback', methods=['GET', 'POST'])
def discord_login_callback():
    if request.method == 'GET':
        token = discord.authorize_access_token()
        user_data = discord.get('users/@me').json()
        user = User.query.filter_by(discord_id=user_data['id']).first()
        if user:
            login_user(user)
            flash(_('Logged in with Discord.'), 'success')
            return redirect(url_for('post.feed'))
        else:
            flash(_('No account linked with this Discord. Please register.'), 'info')
            return render_template(
                'discord_register.html',
                username=user_data['username'],
                email=user_data.get('email', ''),
                discord_id=user_data['id']
            )
    else:
        username = request.form.get('username')
        email = request.form.get('email')
        discord_id = request.form.get('discord_id')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not password or len(password) < 8:
            flash(_('Password must be at least 8 characters long.'), 'danger')
            return render_template('discord_register.html', username=username, email=email, discord_id=discord_id)
        if password != confirm_password:
            flash(_('Passwords do not match.'), 'danger')
            return render_template('discord_register.html', username=username, email=email, discord_id=discord_id)
        if db.session.query(User).filter_by(username=username).first():
            flash(_('Username already exists. Please Report It.'), 'danger')
            return render_template('discord_register.html', username="", email=email, discord_id=discord_id)
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            discord_id=discord_id,
            discord_linked=True
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash(_('Account created and logged in with Discord.'), 'success')
        return redirect(url_for('post.feed'))

@discord_bp.route('/link_discord')
@login_required
def link_discord():
    redirect_uri = url_for('discord.authorize_discord', _external=True)
    return discord.authorize_redirect(redirect_uri)

@discord_bp.route('/authorize/discord')
@login_required
def authorize_discord():
    token = discord.authorize_access_token()
    user_data = discord.get('users/@me').json()
    current_user.discord_id = user_data['id']
    current_user.discord_linked = True
    db.session.commit()
    flash(_('Discord account linked!'), 'success')
    return redirect(url_for('profil.profile'))

@discord_bp.route('/unlink_discord', methods=['POST'])
@login_required
def unlink_discord():
    current_user.discord_id = None
    current_user.discord_linked = False
    db.session.commit()
    flash(_('Discord account unlinked!'), 'success')
    return redirect(url_for('profil.profile'))