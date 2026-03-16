"""
Earl's Landscaping API - Fixed for Vercel Serverless
"""
from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import os

app = Flask(__name__)

# DEBUG: Print environment info at startup
print(f"ENV KEYS: {list(os.environ.keys())}")
print(f"MONGODB_URI present: {'MONGODB_URI' in os.environ}")
print(f"MONGO_URL present: {'MONGO_URL' in os.environ}")

# Lazy config loader
_config = {}

def get_config(key, default=''):
    if key not in _config:
        _config[key] = os.environ.get(key, default)
    return _config[key]

def init_config():
    """Initialize all config at startup"""
    _config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'default-secret')
    _config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME', 'shahbaz')
    _config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'Shaherzad123!')
    _config['MONGO_URL'] = os.environ.get('MONGODB_URI') or os.environ.get('MONGO_URL', '')
    _config['DB_NAME'] = os.environ.get('DB_NAME', 'atlas-pink-xylophone')
    _config['RESEND_API_KEY'] = os.environ.get('RESEND_API_KEY', '')
    _config['FROM_EMAIL'] = os.environ.get('FROM_EMAIL', 'onboarding@resend.dev')
    return _config

# Call at startup
init_config()

# CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,PATCH,OPTIONS')
    return response

# MongoDB connection (lazy)
db = None
db_available = False

def get_db():
    global db, db_available
    if db is None:
        # Get MongoDB URI - try MONGODB_URI first (Vercel MongoDB integration)
        mongo_url = os.environ.get('MONGODB_URI') or os.environ.get('MONGO_URL', '')
        db_name = os.environ.get('DB_NAME', 'atlas-pink-xylophone')
        
        print(f"Connecting to MongoDB... URL set: {bool(mongo_url)}")
        
        if mongo_url:
            try:
                from pymongo import MongoClient
                client = MongoClient(mongo_url)
                # Test connection
                client.admin.command('ping')
                db = client[db_name]
                db_available = True
                print("MongoDB connected successfully!")
            except Exception as e:
                print(f"MongoDB connection failed: {e}")
                db_available = False
        else:
            print("No MongoDB URL configured")
    return db

# ============== AUTH ==============

def generate_token(username):
    payload = {
        'sub': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, get_config('JWT_SECRET'), algorithm='HS256')

def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.replace('Bearer ', '')
    try:
        return jwt.decode(token, get_config('JWT_SECRET'), algorithms=['HS256'])
    except:
        return None

# ============== ROUTES ==============

@app.route('/')
def root():
    mongo_set = bool(get_config('MONGO_URL'))
    return jsonify({
        "message": "Earl's Landscaping API",
        "status": "ok",
        "db_configured": mongo_set,
        "db_connected": db_available
    })

@app.route('/api/')
def api_root():
    return jsonify({
        "message": "Earl's Landscaping API",
        "status": "ok",
        "db_configured": bool(get_config('MONGO_URL')),
        "db_connected": db_available
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
        required = ['name', 'email', 'phone', 'service_type']
        if not all(r in data for r in required):
            return jsonify({"success": False, "message": "Missing fields"}), 400
        
        lead = {
            "_id": str(uuid.uuid4()),
            "name": data['name'],
            "email": data['email'],
            "phone": data['phone'],
            "service_type": data['service_type'],
            "status": "new",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Save to MongoDB
        db = get_db()
        if db:
            db.leads.insert_one(lead)
        
        # Send email
        resend_key = get_config('RESEND_API_KEY')
        if resend_key:
            try:
                import resend
                resend.api_key = resend_key
                resend.Emails.send({
                    "from": get_config('FROM_EMAIL'),
                    "to": ['vevadeco@gmail.com'],
                    "subject": "New Lead - Earl's Landscaping",
                    "html": f"<h2>New Lead</h2><p>Name: {lead['name']}</p><p>Email: {lead['email']}</p><p>Phone: {lead['phone']}</p><p>Service: {lead['service_type']}</p>"
                })
            except:
                pass
        
        return jsonify({"success": True, "message": "Lead created"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login/', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    data = request.get_json() or {}
    if data.get('username') == get_config('ADMIN_USERNAME') and data.get('password') == get_config('ADMIN_PASSWORD'):
        token = generate_token(data['username'])
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/auth/verify/')
def verify():
    payload = verify_token()
    if payload:
        return jsonify({"valid": True})
    return jsonify({"valid": False}), 401

@app.route('/api/admin/leads', methods=['GET', 'OPTIONS'])
@app.route('/api/admin/leads/', methods=['GET', 'OPTIONS'])
def get_leads():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        db = get_db()
        if not db:
            return jsonify([])
        
        leads = list(db.leads.find({}, {'_id': 0}).sort('created_at', -1))
        for lead in leads:
            if isinstance(lead.get('created_at'), datetime):
                lead['created_at'] = lead['created_at'].isoformat()
        return jsonify(leads)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
