from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from bson.objectid import ObjectId

from .mongo_user import MongoUser
from . import mongo, login_manager

auth_bp = Blueprint('auth', __name__)


# =========================================================
# LOGIN MANAGER USER LOADER
# =========================================================
@login_manager.user_loader
def load_user(user_id):
    user = mongo.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if user:
        return MongoUser(user)

    return None


# =========================================================
# LOGIN PAGE
# =========================================================
@auth_bp.route('/login')
def login():
    return render_template('login.html')


# =========================================================
# SIGNUP PAGE
# =========================================================
@auth_bp.route('/signup')
def signup():
    return render_template('signup.html')


# =========================================================
# API SIGNUP
# =========================================================
@auth_bp.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()

    if not username or not email or not phone or not password:
        return jsonify({
            "status": "error",
            "message": "All fields are required"
        }), 400

    existing_user = mongo.db.users.find_one({
        "$or": [
            {"username": username},
            {"email": email}
        ]
    })

    if existing_user:
        return jsonify({
            "status": "error",
            "message": "Username or email already exists"
        }), 400

    hashed_password = generate_password_hash(password)

    mongo.db.users.insert_one({
        "username": username,
        "email": email,
        "phone": phone,
        "password_hash": hashed_password,
        "is_admin": False
    })

    return jsonify({
        "status": "success",
        "message": "Account created successfully"
    })


# =========================================================
# API LOGIN
# =========================================================
@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Username and password required"
        }), 400

    user = mongo.db.users.find_one({
        "username": username
    })

    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404

    if not check_password_hash(user["password_hash"], password):
        return jsonify({
            "status": "error",
            "message": "Invalid password"
        }), 401

    login_user(MongoUser(user))

    return jsonify({
        "status": "success",
        "next": "/dashboard"
    })


# =========================================================
# LOGOUT
# =========================================================
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))