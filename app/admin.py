from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import User, Document
from . import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
def admin_index():
    if not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('main.dashboard'))
    users = User.query.all()
    docs = Document.query.order_by(Document.uploaded_at.desc()).all()
    return render_template('admin.html', users=users, docs=docs)
