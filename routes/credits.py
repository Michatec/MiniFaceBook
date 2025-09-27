from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from flask_babel import gettext as _

credits_bp = Blueprint('credit', __name__)

@credits_bp.route('/credits')
def credits():
    return render_template('credits.html')

@credits_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')