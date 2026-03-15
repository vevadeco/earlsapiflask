"""
Earl's Landscaping API - Fixed Version
"""
from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import os
import traceback

app = Flask(__name__)

# Manual CORS handler
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

# In-memory storage
leads_db = []
page_views = []

print(f"Starting Earl's API - Admin: {ADMIN_USERNAME}")

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
    return jsonify({"message": "Earl's Landscaping API", "status": "ok"})

@app.route('/api/', methods=['GET', 'OPTIONS'])
def api_root():
    return jsonify({"message": "Earl's Landscaping API", "status": "ok"})

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
        print(f"Creating lead: {data}")
        
        required = ['name', 'email', 'phone', 'service_type']
        if not all(r in data for r in required):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        lead = {
            "id": str(uuid.uuid4()),
            "name": data['name'],
            "email": data['email'],
            "phone": data['phone'],
            "service_type": data['service_type'],
            "status": "new",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        leads_db.append(lead)
        print(f"Lead created: {lead['id']}, Total leads: {len(leads_db)}")
        
        return jsonify({"success": True, "message": "Lead created", "lead_id": lead['id']})
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/analytics/pageview/', methods=['POST', 'OPTIONS'])
def track_pageview():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    data = request.get_json() or {}
    page_view = {
        "id": str(uuid.uuid4()),
        "page": data.get('page', '/'),
        "referrer": data.get('referrer'),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    page_views.append(page_view)
    return jsonify({"success": True})

# ============== AUTH ROUTES ==============

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login/', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    print(f"Login attempt: {username}")
    
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
    
    return jsonify(leads_db)

@app.route('/api/admin/leads/<lead_id>/status/', methods=['PATCH', 'OPTIONS'])
def update_lead_status(lead_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    
    for lead in leads_db:
        if lead['id'] == lead_id:
            lead['status'] = data.get('status', 'new')
            return jsonify({"success": True})
    
    return jsonify({"error": "Lead not found"}), 404

@app.route('/api/admin/analytics/', methods=['GET', 'OPTIONS'])
def get_analytics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today.isoformat()
    
    leads_today = [l for l in leads_db if l.get('created_at', '').startswith(today_str[:10])]
    
    return jsonify({
        "total_visitors": len(page_views),
        "total_leads": len(leads_db),
        "visitors_today": 0,
        "leads_today": len(leads_today),
        "conversion_rate": 0,
        "daily_stats": []
    })

# ============== ERROR HANDLERS ==============

@app.errorhandler(404)
def not_found(e):
    print(f"404: {request.path}")
    return jsonify({"error": "Not found", "path": request.path}), 404

@app.errorhandler(500)
def server_error(e):
    print(f"500: {e}")
    return jsonify({"error": "Server error", "message": str(e)}), 500

# Vercel handler
if __name__ == '__main__':
    app.run(debug=True)
