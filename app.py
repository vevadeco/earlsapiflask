"""
Earl's Landscaping API - Debug Version
"""
from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import os
import traceback

app = Flask(__name__)

# Debug: print env vars at startup
print(f"=== ENVIRONMENT ===")
print(f"All env keys: {list(os.environ.keys())}")
print(f"MONGODB_URI set: {bool(os.environ.get('MONGODB_URI'))}")
print(f"MONGO_URL set: {bool(os.environ.get('MONGO_URL'))}")
print(f"DB_NAME: {os.environ.get('DB_NAME', 'NOT SET')}")

# Store connection error globally
db_connection_error = None

# MongoDB connection
db = None
db_available = False

def get_db():
    global db, db_available, db_connection_error
    if db is None:
        mongo_url = os.environ.get('MONGODB_URI') or os.environ.get('MONGO_URL', '')
        db_name = os.environ.get('DB_NAME', 'atlas-pink-xylophone')
        
        if mongo_url:
            try:
                from pymongo import MongoClient
                client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
                client.admin.command('ping')
                db = client[db_name]
                db_available = True
            except Exception as e:
                db_connection_error = str(e)
                print(f"MongoDB Error: {e}")
    return db

# CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,PATCH,OPTIONS')
    return response

# Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret')
ADMIN_USER = os.environ.get('ADMIN_USERNAME', 'shahbaz')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'Shaherzad123!')

# ============== ROUTES ==============

@app.route('/')
@app.route('/api/')
def root():
    get_db()  # Try to connect
    return jsonify({
        "message": "Earl's Landscaping API",
        "status": "ok",
        "db_configured": bool(os.environ.get('MONGODB_URI') or os.environ.get('MONGO_URL')),
        "db_connected": db_available,
        "db_error": db_connection_error,
        "env_keys": list(os.environ.keys())[:10]
    })

@app.route('/api/promo-banner/')
def get_promo():
    return jsonify({
        "enabled": True,
        "title": "Spring Cleanup Special - 15% OFF!",
        "subtitle": "Book by March 1st to save",
        "discount_text": "15% OFF",
        "deadline_date": "2026-03-01"
    })

@app.route('/api/leads', methods=['POST', 'OPTIONS'])
@app.route('/api/leads/', methods=['POST', 'OPTIONS'])
def create_lead():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json() or {}
        db = get_db()
        
        lead = {
            "_id": str(uuid.uuid4()),
            "name": data.get('name'),
            "email": data.get('email'),
            "phone": data.get('phone'),
            "service_type": data.get('service_type'),
            "status": "new",
            "created_at": datetime.now(timezone.utc)
        }
        
        if db:
            db.leads.insert_one(lead)
            return jsonify({"success": True, "message": "Lead created"})
        else:
            return jsonify({"success": False, "message": "Database not connected", "error": db_connection_error}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login/', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    data = request.get_json() or {}
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        token = jwt.encode({
            'sub': data['username'],
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }, JWT_SECRET, algorithm='HS256')
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

# Error handlers
@app.errorhandler(Exception)
def handle_error(e):
    import traceback
    return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
