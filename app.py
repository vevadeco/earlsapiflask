"""
Earl's Landscaping API - Flask Version
"""
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
CORS(app)

# Config
app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'default-secret')
app.config['ADMIN_USERNAME'] = os.environ.get('ADMIN_USERNAME', 'shahbaz')
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'Shaherzad123!')

# MongoDB - lazy connection
client = None
db = None

def get_db():
    global client, db
    if db is None:
        mongo_url = os.environ.get('MONGO_URL')
        if not mongo_url:
            return None
        client = MongoClient(mongo_url)
        db = client[os.environ.get('DB_NAME', 'earls_prod')]
    return db

# Middleware to check DB
def require_db():
    db = get_db()
    if db is None:
        return jsonify({"error": "Database not configured"}), 500
    return db

# ============== AUTH ==============

def generate_token(username):
    payload = {
        'sub': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

def verify_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.replace('Bearer ', '')
    try:
        return jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
    except:
        return None

# ============== PUBLIC ROUTES ==============

@app.route('/')
def root():
    return jsonify({"message": "Earl's Landscaping API", "status": "ok"})

@app.route('/api/')
def api_root():
    db = get_db()
    return jsonify({
        "message": "Earl's Landscaping API",
        "status": "ok",
        "db_connected": db is not None
    })

@app.route('/api/promo-banner/', methods=['GET'])
def get_promo():
    return jsonify({
        "enabled": True,
        "title": "Spring Cleanup Special - 15% OFF!",
        "subtitle": "Book by March 1st to save",
        "discount_text": "15% OFF",
        "cta_text": "Claim Offer",
        "deadline_date": "2026-03-01"
    })

@app.route('/api/leads/', methods=['POST'])
def create_lead():
    data = request.get_json() or {}
    
    # Validate
    required = ['name', 'email', 'phone', 'service_type']
    if not all(r in data for r in required):
        return jsonify({"success": False, "message": "Missing required fields"}), 400
    
    db = get_db()
    if db is None:
        # Store in memory if no DB
        return jsonify({"success": True, "message": "Lead received", "lead_id": str(uuid.uuid4())})
    
    lead = {
        "id": str(uuid.uuid4()),
        "name": data['name'],
        "email": data['email'],
        "phone": data['phone'],
        "service_type": data['service_type'],
        "status": "new",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    db.leads.insert_one(lead)
    return jsonify({"success": True, "message": "Lead created", "lead_id": lead['id']})

# ============== AUTH ROUTES ==============

@app.route('/api/auth/login/', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
        token = generate_token(username)
        return jsonify({"success": True, "token": token, "message": "Login successful"})
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/auth/verify/', methods=['GET'])
def verify():
    payload = verify_token()
    if payload:
        return jsonify({"valid": True, "username": payload.get('sub')})
    return jsonify({"valid": False}), 401

# ============== ADMIN ROUTES ==============

@app.route('/api/admin/leads/', methods=['GET'])
def get_leads():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    if db is None:
        return jsonify([])
    
    leads = list(db.leads.find({}, {'_id': 0}).sort('created_at', -1))
    return jsonify(leads)

@app.route('/api/admin/leads/<lead_id>/status/', methods=['PATCH'])
def update_lead_status(lead_id):
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    db = get_db()
    
    if db:
        db.leads.update_one({"id": lead_id}, {"$set": {"status": data.get('status', 'new')}})
    
    return jsonify({"success": True})

@app.route('/api/admin/analytics/', methods=['GET'])
def get_analytics():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    if db is None:
        return jsonify({
            "total_visitors": 0,
            "total_leads": 0,
            "visitors_today": 0,
            "leads_today": 0,
            "daily_stats": []
        })
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_leads = db.leads.count_documents({})
    leads_today = db.leads.count_documents({"created_at": {"$gte": today.isoformat()}})
    
    return jsonify({
        "total_visitors": 0,
        "total_leads": total_leads,
        "visitors_today": 0,
        "leads_today": leads_today,
        "conversion_rate": 0,
        "daily_stats": []
    })

# ============== ERROR HANDLERS ==============

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error", "message": str(e)}), 500

# Vercel handler
if __name__ == '__main__':
    app.run(debug=True)
