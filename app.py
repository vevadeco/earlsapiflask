"""
Earl's Landscaping - Combined Backend + Frontend
Single Vercel deployment - Flask serves both API and React frontend
"""
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timezone, timedelta
import uuid
import jwt
import os
import traceback

app = Flask(__name__, static_folder='build', static_url_path='')

# ============== CONFIG ==============
JWT_SECRET = os.environ.get('JWT_SECRET') or os.environ.get('SECRET_KEY') or ''
ADMIN_USER = os.environ.get('ADMIN_USERNAME') or ''
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD') or ''

# ============== CORS ==============
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# ============== MONGODB ==============
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
            except:
                pass
    return db

# ============== API ROUTES ==============

@app.route('/api/health')
def health():
    return jsonify({
        "status": "ok",
        "db_connected": db_available,
        "version": "combined-1.0"
    })

@app.route('/api/')
def api_root():
    return jsonify({
        "message": "Earl's Landscaping API",
        "status": "ok",
        "db_connected": db_available
    })

@app.route('/api/promo-banner', methods=['GET', 'OPTIONS'])
@app.route('/api/promo-banner/', methods=['GET', 'OPTIONS'])
def get_promo():
    return jsonify({
        "enabled": True,
        "title": "Spring Cleanup Special - 15% OFF!",
        "subtitle": "Book by March 1st to save",
        "discount_text": "15% OFF",
        "deadline_date": "2026-03-01"
    })

@app.route('/api/analytics/pageview', methods=['POST', 'OPTIONS'])
@app.route('/api/analytics/pageview/', methods=['POST', 'OPTIONS'])
def track_pageview():
    return jsonify({"success": True})

@app.route('/api/leads', methods=['POST', 'OPTIONS'])
@app.route('/api/leads/', methods=['POST', 'OPTIONS'])
def create_lead():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json(force=True, silent=True) or {}
        db = get_db()
        if not db:
            return jsonify({"success": False, "message": "Database not configured"}), 503
        
        lead = {
            "_id": str(uuid.uuid4()),
            "name": data.get('name'),
            "email": data.get('email'),
            "phone": data.get('phone'),
            "service_type": data.get('service_type'),
            "status": "new",
            "created_at": datetime.now(timezone.utc)
        }
        
        db.leads.insert_one(lead)
        
        return jsonify({"success": True, "message": "Lead created"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@app.route('/api/auth/login/', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    if not JWT_SECRET or not ADMIN_USER or not ADMIN_PASS:
        return jsonify({"success": False, "message": "Server misconfigured: set JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD"}), 500
    
    data = request.get_json(force=True, silent=True) or {}
    
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        token = jwt.encode({
            'sub': data['username'],
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }, JWT_SECRET, algorithm='HS256')
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/admin/leads', methods=['GET', 'OPTIONS'])
@app.route('/api/admin/leads/', methods=['GET', 'OPTIONS'])
def get_leads():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    if not JWT_SECRET:
        return jsonify({"error": "Server misconfigured: set JWT_SECRET"}), 500
    
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        jwt.decode(auth.replace('Bearer ', ''), JWT_SECRET, algorithms=['HS256'])
    except:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    if not db:
        return jsonify([])
    
    leads = list(db.leads.find({}, {'_id': 0}).sort('created_at', -1))
    for lead in leads:
        if isinstance(lead.get('created_at'), datetime):
            lead['created_at'] = lead['created_at'].isoformat()
    return jsonify(leads)

# ============== SERVE FRONTEND ==============

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React app for all non-API routes"""
    if path.startswith('api/'):
        return jsonify({"error": "API route not found"}), 404
    
    # Serve static files from build folder
    static_file = os.path.join(app.static_folder, path)
    if path and os.path.exists(static_file) and os.path.isfile(static_file):
        return send_from_directory(app.static_folder, path)
    
    # Otherwise serve index.html (React handles routing)
    return send_from_directory(app.static_folder, 'index.html')

# For development
if __name__ == '__main__':
    app.run(debug=True, port=5000)
