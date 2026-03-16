"""
Earl's Landscaping API - With MongoDB
"""
from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import os
import traceback

app = Flask(__name__)

# CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,PATCH,OPTIONS')
    return response

# Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'shahbaz')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Shaherzad123!')
MONGO_URL = os.environ.get('MONGO_URL', '')
DB_NAME = os.environ.get('DB_NAME', 'earls_prod')

print(f"API Starting - MongoDB: {'Connected' if MONGO_URL else 'Not configured'}")

# MongoDB connection (lazy)
db = None
db_available = False

def get_db():
    global db, db_available
    if db is None and MONGO_URL:
        try:
            from pymongo import MongoClient
            client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            # Test connection
            client.server_info()
            db = client[DB_NAME]
            db_available = True
            print("MongoDB connected successfully")
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
            db_available = False
    return db

# ============== AUTH ==============

def generate_token(username):
    payload = {
        'sub': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.replace('Bearer ', '')
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except:
        return None

# ============== PUBLIC ROUTES ==============

@app.route('/', methods=['GET', 'OPTIONS'])
def root():
    return jsonify({"message": "Earl's Landscaping API", "status": "ok", "db": db_available})

@app.route('/api/', methods=['GET', 'OPTIONS'])
def api_root():
    return jsonify({"message": "Earl's Landscaping API", "status": "ok", "db": db_available})

@app.route('/api/promo-banner/', methods=['GET', 'OPTIONS'])
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
        print(f"Creating lead: {data.get('email')}")
        
        required = ['name', 'email', 'phone', 'service_type']
        if not all(r in data for r in required):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
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
            try:
                db.leads.insert_one(lead)
                print(f"Lead saved to MongoDB: {lead['_id']}")
            except Exception as e:
                print(f"MongoDB save failed: {e}")
                return jsonify({"success": False, "message": "Database error"}), 500
        else:
            print("No database available")
            return jsonify({"success": False, "message": "Database not configured"}), 500
        
        return jsonify({"success": True, "message": "Lead created", "lead_id": lead['_id']})
    except Exception as e:
        print(f"Error creating lead: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": str(e)}), 500

# ============== AUTH ROUTES ==============

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login/', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = generate_token(username)
        return jsonify({"success": True, "token": token, "message": "Login successful"})
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/auth/verify/', methods=['GET', 'OPTIONS'])
def verify():
    payload = verify_token()
    if payload:
        return jsonify({"valid": True, "username": payload.get('sub')})
    return jsonify({"valid": False}), 401

# ============== ADMIN ROUTES ==============

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
            return jsonify({"error": "Database not available"}), 500
        
        leads = list(db.leads.find({}, {'_id': 0}).sort('created_at', -1))
        
        # Convert datetime to string for JSON serialization
        for lead in leads:
            if isinstance(lead.get('created_at'), datetime):
                lead['created_at'] = lead['created_at'].isoformat()
        
        print(f"Retrieved {len(leads)} leads")
        return jsonify(leads)
    except Exception as e:
        print(f"Error retrieving leads: {e}")
        return jsonify({"error": str(e)}), 500

# ============== ERROR HANDLERS ==============

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "path": request.path}), 404

@app.errorhandler(500)
def server_error(e):
    print(f"500 error: {e}")
    return jsonify({"error": "Server error"}), 500
