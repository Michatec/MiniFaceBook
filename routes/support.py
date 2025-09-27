from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from models import db, SupportComment, SupportRequest
from flask_babel import gettext as _
from flask_login import login_required, current_user
from datetime import datetime

support_bp = Blueprint('support', __name__, url_prefix="/support")

@support_bp.route('/', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if description and title:
            ticket = SupportRequest(
                user_id=current_user.id,
                title=title,
                status='open',
                created_at=datetime.now()
            )
            db.session.add(ticket)
            db.session.commit()
            db.session.add(SupportComment(request_id=ticket.id, user_id=current_user.id, message=description, created_at=datetime.now()))
            db.session.commit()
            flash(_('Support request created!'), 'success')
        else:
            flash(_('Title and message required!'), 'danger')

    if current_user.is_admin:
        support_requests = db.session.query(SupportRequest).order_by(SupportRequest.created_at.desc()).all()
    else:
        support_requests = db.session.query(SupportRequest).filter_by(user_id=current_user.id).order_by(SupportRequest.created_at.desc()).all()
    return render_template('support.html', support_requests=support_requests)

@support_bp.route('/close/<int:request_id>', methods=['POST'])
@login_required
def support_close(request_id):
    ticket = db.session.get(SupportRequest, request_id)
    if not ticket or (not current_user.is_admin and ticket.user_id != current_user.id):
        abort(403)
    ticket.status = 'closed'
    db.session.commit()
    flash(_('Ticket closed.'), 'success')
    return redirect(url_for('support.support_thread', request_id=request_id))

@support_bp.route('/thread/<int:request_id>', methods=['GET', 'POST'])
@login_required
def support_thread(request_id):
    ticket = db.session.get(SupportRequest, request_id)
    if not ticket or (not current_user.is_admin and ticket.user_id != current_user.id):
        abort(403)
    if request.method == 'POST' and ticket.status == 'open':
        message = request.form.get('message')
        if message:
            db.session.add(SupportComment(request_id=request_id, user_id=current_user.id, message=message, created_at=datetime.now()))
            db.session.commit()
            flash(_('Comment added.'), 'success')
        else:
            flash(_('Message required!'), 'danger')
    comments = db.session.query(SupportComment).filter_by(request_id=request_id).order_by(SupportComment.created_at.asc()).all()
    return render_template('support_thread.html', ticket=ticket, comments=comments)

@support_bp.route('/delete/<int:request_id>', methods=['POST'])
@login_required
def support_delete(request_id):
    if not current_user.is_admin:
        abort(403)
    ticket = db.session.get(SupportRequest, request_id)
    if ticket:
        db.session.query(SupportComment).filter_by(request_id=request_id).delete()
        db.session.delete(ticket)
        db.session.commit()
        flash(_('Support ticket deleted.'), 'success')
    else:
        flash(_('Ticket not found.'), 'danger')
    return redirect(url_for('support.support'))