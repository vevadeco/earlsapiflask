"""
Earl's Landscaping API
"""
from flask import Flask, request, jsonify, make_response
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import os

app = Flask(__name__)

# Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret')
ADMIN_USER = os.environ.get('ADMIN_USERNAME', 'shahbaz')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'Shaherzad123!')

# MongoDB
db = None
db_available = False

def get_db():
    global db, db_available
    if db is None:
        mongo_url = os.environ.get('MONGODB_URI') or os.environ.get('MONGO_URL', '')
        db_name = os.environ.get('DB_NAME', 'atlas-pink-xylophone')
        if mongo_url:
            try:
                from pymongo import MongoClient
                client = MongoClient(mongo_url)
                client.admin.command('ping')
                db = client[db_name]
                db_available = True
            except Exception as e:
                print(f"DB error: {e}")
    return db

def cors_response(data, status=200):
    response = make_response(jsonify(data), status)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

# Handle OPTIONS for all routes
@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        return cors_response({})

@app.route('/', methods=['GET', 'OPTIONS'])
def root():
    if request.method == 'OPTIONS':
        return cors_response({})
    get_db()
    return cors_response({
        "message": "Earl's Landscaping API",
        "status": "ok",
        "db_connected": db_available
    })

@app.route('/api/', methods=['GET', 'OPTIONS'])
def api_root():
    return cors_response({
        "message": "Earl's Landscaping API",
        "status": "ok",
        "db_connected": db_available
    })

# Promo banner - both with and without trailing slash
@app.route('/api/promo-banner', methods=['GET', 'OPTIONS'])
@app.route('/api/promo-banner/', methods=['GET', 'OPTIONS'])
def get_promo():
    return cors_response({
        "enabled": True,
        "title": "Spring Cleanup Special - 15% OFF!",
        "subtitle": "Book by March 1st to save",
        "discount_text": "15% OFF",
        "deadline_date": "2026-03-01"
    })

# Analytics - both with and without trailing slash
@app.route('/api/analytics/pageview', methods=['POST', 'OPTIONS'])
@app.route('/api/analytics/pageview/', methods=['POST', 'OPTIONS'])
def track_pageview():
    return cors_response({"success": True})

# Leads - both with and without trailing slash
@app.route('/api/leads', methods=['POST', 'OPTIONS'])
@app.route('/api/leads/', methods=['POST', 'OPTIONS'])
def create_lead():
    try:
        data = request.get_json(force=True, silent=True) or {}
        print(f"LEAD DATA: {data}")
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
            print(f"SAVED: {lead['_id']}")
        else:
            print("NO DB - not saved")
        
        return cors_response({"success": True, "message": "Lead created"})
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return cors_response({"success": False, "message": str(e)}, 500)

# Login - both with and without trailing slash
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login/', methods=['POST', 'OPTIONS'])
def login():
    data = request.get_json(force=True, silent=True) or {}
    print(f"LOGIN: {data.get('username')}")
    
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        token = jwt.encode({
            'sub': data['username'],
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }, JWT_SECRET, algorithm='HS256')
        return cors_response({"success": True, "token": token})
    return cors_response({"success": False, "message": "Invalid credentials"}, 401)

# Admin leads - both with and without trailing slash
@app.route('/api/admin/leads', methods=['GET', 'OPTIONS'])
@app.route('/api/admin/leads/', methods=['GET', 'OPTIONS'])
def get_leads():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return cors_response({"error": "Unauthorized - no token"}, 401)
    
    try:
        jwt.decode(auth.replace('Bearer ', ''), JWT_SECRET, algorithms=['HS256'])
    except:
        return cors_response({"error": "Unauthorized - invalid token"}, 401)
    
    db = get_db()
    if not db:
        return cors_response([])
    
    try:
        leads = list(db.leads.find({}, {'_id': 0}).sort('created_at', -1))
        for lead in leads:
            if isinstance(lead.get('created_at'), datetime):
                lead['created_at'] = lead['created_at'].isoformat()
        return cors_response(leads)
    except Exception as e:
        print(f"GET_LEADS ERROR: {e}")
        return cors_response({"error": str(e)}, 500)
