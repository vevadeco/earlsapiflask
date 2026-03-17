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

# Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret')
ADMIN_USER = os.environ.get('ADMIN_USERNAME', 'shahbaz')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'Shaherzad123!')

# CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

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

# API ROUTES
@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "db_connected": db_available})

@app.route('/api/')
def api_root():
    return jsonify({"message": "Earl's API", "status": "ok", "db_connected": db_available})

@app.route('/api/promo-banner')
def get_promo():
    return jsonify({
        "enabled": True,
        "title": "Spring Cleanup Special - 15% OFF!",
        "subtitle": "Book by March 1st to save",
        "discount_text": "15% OFF",
        "deadline_date": "2026-03-01"
    })

@app.route('/api/analytics/pageview', methods=['POST'])
def track_pageview():
    return jsonify({"success": True})

@app.route('/api/leads', methods=['POST'])
def create_lead():
    try:
        data = request.get_json(force=True, silent=True) or {}
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
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True) or {}
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        token = jwt.encode({
            'sub': data['username'],
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }, JWT_SECRET, algorithm='HS256')
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/admin/leads')
def get_leads():
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
    return jsonify(leads)

# FRONTEND - Catch all routes and serve React
@app.route('/')
def index():
    """Serve index.html for root"""
    return send_from_directory('build', 'index.html')

@app.route('/<path:path>')
def catch_all(path):
    """Handle React Router routes and static files"""
    # API routes should be handled above, but if they fall through:
    if path.startswith('api/'):
        return jsonify({"error": "API endpoint not found"}), 404
    
    # Try to serve as static file first
    try:
        return send_from_directory('build', path)
    except:
        # Not a static file, serve index.html for React Router
        return send_from_directory('build', 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
