#!/usr/bin/env python3
"""
AERIS 2.1 - Unified Backend Server & RESTful API
Campus Facility Management & Environmental Intelligence Platform
Universitas Multimedia Nusantara (UMN)

Features:
- Pure Python 3 standard library with SQLite (zero external dependencies required)
- Serves static assets, HTML pages, styles, scripts, and uploaded files
- Full RESTful API under /api/v1/...
- PBKDF2 SHA-256 salted password hashing & session management
- Profile picture uploads with validation (JPG, PNG, WebP, max 2MB)
- Automated achievement calculation, unlocking, and notifications
- Environmental Radar & crowd comfort calculations
- Real QR code generation & placard metadata
- Interactive Swagger / OpenAPI documentation at /api/docs/
"""

import os
import sys
import json
import time
import uuid
import base64
import sqlite3
import hashlib
import binascii
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "aeris.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Database Engine & Schema Initializer
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        xp INTEGER NOT NULL DEFAULT 0,
        level_number INTEGER NOT NULL DEFAULT 1,
        student_nim TEXT,
        faculty_dept TEXT DEFAULT 'Faculty of Engineering & Informatics',
        avatar_url TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS rooms (
        id TEXT PRIMARY KEY,
        room_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        building TEXT NOT NULL,
        floor INTEGER NOT NULL DEFAULT 1,
        room_type TEXT NOT NULL DEFAULT 'Study Space',
        capacity INTEGER NOT NULL DEFAULT 50,
        walk_time TEXT DEFAULT '3 min walk',
        image_url TEXT DEFAULT 'assets/library.jpg',
        qr_code TEXT UNIQUE NOT NULL,
        qr_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS room_telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        temperature REAL NOT NULL,
        humidity REAL NOT NULL,
        co2 INTEGER NOT NULL,
        pm25 REAL DEFAULT 10.0,
        noise_level REAL DEFAULT 45.0,
        tvoc INTEGER DEFAULT 75,
        occupancy REAL NOT NULL DEFAULT 0.0,
        tables_available INTEGER DEFAULT 10,
        comfort_score INTEGER NOT NULL DEFAULT 85,
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS room_equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        serial_number TEXT,
        category TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Operational',
        installed_at DATE,
        last_inspected_at DATETIME
    );

    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        room_id TEXT NOT NULL REFERENCES rooms(id),
        reporter_id INTEGER REFERENCES users(id),
        reporter_name TEXT NOT NULL,
        reporter_role TEXT NOT NULL DEFAULT 'student',
        category TEXT NOT NULL,
        issue TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL DEFAULT 'MEDIUM',
        status TEXT NOT NULL DEFAULT 'Submitted',
        photo_url TEXT,
        admin_notes TEXT,
        technician_notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME
    );

    CREATE TABLE IF NOT EXISTS verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
        room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        response TEXT NOT NULL,
        verified_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS thermal_feedback (
        id TEXT PRIMARY KEY,
        room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        rating TEXT NOT NULL,
        temp_snapshot REAL,
        hum_snapshot REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS maintenance_tasks (
        id TEXT PRIMARY KEY,
        report_id TEXT REFERENCES reports(id),
        room_id TEXT NOT NULL REFERENCES rooms(id),
        title TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL DEFAULT 'Facility Maintenance',
        priority TEXT NOT NULL DEFAULT 'MEDIUM',
        status TEXT NOT NULL DEFAULT 'Pending',
        assigned_to TEXT NOT NULL,
        created_by TEXT DEFAULT 'Facility Admin',
        start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        expected_completion DATETIME,
        completion_date DATETIME,
        resolution_photo TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS maintenance_logs (
        id TEXT PRIMARY KEY,
        room_id TEXT NOT NULL REFERENCES rooms(id),
        room_name TEXT NOT NULL,
        report_id TEXT REFERENCES reports(id),
        task_id TEXT REFERENCES maintenance_tasks(id),
        event_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        actor TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        badge TEXT DEFAULT 'Update',
        logged_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS achievements (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        icon TEXT NOT NULL,
        target_metric TEXT NOT NULL,
        target_count INTEGER NOT NULL,
        xp_reward INTEGER NOT NULL DEFAULT 50,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        achievement_id TEXT NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
        unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        notified INTEGER NOT NULL DEFAULT 0,
        UNIQUE(user_id, achievement_id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'system',
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        icon TEXT DEFAULT '🔔',
        link TEXT,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id TEXT PRIMARY KEY,
        music_enabled INTEGER NOT NULL DEFAULT 0,
        music_volume INTEGER NOT NULL DEFAULT 40,
        radar_mode_enabled INTEGER NOT NULL DEFAULT 1,
        default_heatmap_layer TEXT NOT NULL DEFAULT 'thermal',
        notifications_enabled INTEGER NOT NULL DEFAULT 1,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL
    );
    """)

    # Seed Baseline Achievements
    achievements = [
        ('first_step', 'First Step', 'Submit your very first verified campus facility report.', 'Reporting', '🌱', 'reports_submitted', 1, 50),
        ('facility_contributor', 'Facility Contributor', 'Submit 5 valid facility reports to help keep UMN running smoothly.', 'Reporting', '📝', 'reports_submitted', 5, 100),
        ('active_reporter', 'Active Reporter', 'Submit 10 valid facility incident reports across campus.', 'Reporting', '⚡', 'reports_submitted', 10, 200),
        ('comfort_scout', 'Comfort Scout', 'Provide 3 thermal comfort ratings to calibrate indoor air quality.', 'Environmental Comfort', '🌡️', 'thermal_feedback', 3, 50),
        ('community_helper', 'Community Helper', 'Provide 10 valid environmental feedback ratings to calibrate campus HVAC.', 'Environmental Comfort', '👥', 'thermal_feedback', 10, 150),
        ('problem_solver', 'Problem Solver', 'Have 5 of your submitted facility reports officially resolved.', 'Reporting', '🛠️', 'reports_resolved', 5, 250),
        ('community_sentinel', 'Community Sentinel', 'Help verify 3 reported facility conditions around campus.', 'Verification', '🛡️', 'verifications', 3, 75),
        ('verification_hero', 'Verification Hero', 'Complete 10 valid crowdsourced facility issue verifications.', 'Verification', '🏆', 'verifications', 10, 200),
        ('facility_champion', 'Facility Champion', 'Reach 1,500 XP and achieve Level 4: Master Campus Steward.', 'Milestone', '👑', 'xp', 1500, 500)
    ]
    cur.executemany("INSERT OR IGNORE INTO achievements (id, title, description, category, icon, target_metric, target_count, xp_reward) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", achievements)

    # Seed Baseline Users (Salted PBKDF2 SHA-256 for password "password")
    salt_hex = "3023e716499874cb37f884a4ee62ae5b"
    hash_hex = hashlib.pbkdf2_hmac('sha256', b"password", binascii.unhexlify(salt_hex), 100000).hex()

    cur.execute("INSERT OR IGNORE INTO users (username, name, email, role, password_hash, salt, xp, level_number, student_nim) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('student', 'Nasira Siddiqa Nurrahman', 'nasira@umn.ac.id', 'student', hash_hex, salt_hex, 425, 2, '00000157334'))
    cur.execute("INSERT OR IGNORE INTO users (username, name, email, role, password_hash, salt, xp, level_number, student_nim) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('admin', 'Facility Operations Team', 'facility@umn.ac.id', 'admin', hash_hex, salt_hex, 1850, 4, 'ADMIN-001'))

    # Seed Default Rooms
    rooms = [
        ('lib2', 'LIB-F2', 'Library — Floor 2', 'Library', 2, 'Library & Quiet Study', 120, '3 min walk', 'assets/library.jpg', 'AERIS-ROOM-LIB2', 1),
        ('canteen', 'SC-C1', 'Campus Canteen & Food Court', 'Student Center', 1, 'Dining & Social Space', 200, '1 min walk', 'assets/student-lounge.png', 'AERIS-ROOM-CANTEEN', 1),
        ('lounge', 'SC-L1', 'Student Lounge', 'Student Center', 1, 'Student Social Lounge', 80, '5 min walk', 'assets/student-lounge.png', 'AERIS-ROOM-LOUNGE', 1),
        ('gedungD', 'GD-L1', 'Gedung D — Lounge', 'Gedung D', 1, 'Open Study Area', 60, '2 min walk', 'assets/gedung-d-lounge.jpg', 'AERIS-ROOM-GD-L1', 1),
        ('studyHall', 'AC-F3', 'Academic Study Hall', 'Academic', 3, 'Collaborative Workspace', 90, '8 min walk', 'assets/study-hall.jpg', 'AERIS-ROOM-AC-F3', 1),
        ('corridor', 'GB-C1', 'Gedung B Corridor', 'Gedung B', 1, 'Semi-Open Transit Area', 40, '2 min walk', 'assets/gedung-b-corridor.jpg', 'AERIS-ROOM-GB-C1', 1),
        ('A101', 'A101', 'Smart Classroom A101', 'Academic', 1, 'Lecture Classroom', 65, '4 min walk', 'assets/study-hall.jpg', 'AERIS-ROOM-A101', 1),
        ('B201', 'B201', 'Multimedia Design Lab B201', 'Gedung B', 2, 'Computer Laboratory', 45, '4 min walk', 'assets/library.jpg', 'AERIS-ROOM-B201', 1),
        ('D302', 'D302', 'Collaborative Studio D302', 'Gedung D', 3, 'Project Workshop Studio', 50, '6 min walk', 'assets/gedung-d-lounge.jpg', 'AERIS-ROOM-D302', 1)
    ]
    cur.executemany("INSERT OR IGNORE INTO rooms (id, room_code, name, building, floor, room_type, capacity, walk_time, image_url, qr_code, qr_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rooms)

    # Seed Default Telemetry
    telemetry = [
        ('lib2', 22.8, 48.0, 520, 5.0, 38.0, 45, 35.0, 24, 94),
        ('canteen', 26.8, 68.0, 950, 18.0, 68.0, 160, 85.0, 4, 62),
        ('lounge', 24.2, 55.0, 680, 8.0, 52.0, 80, 45.0, 12, 88),
        ('gedungD', 25.5, 63.0, 780, 12.0, 49.0, 110, 60.0, 8, 76),
        ('studyHall', 23.1, 51.0, 610, 6.0, 42.0, 65, 40.0, 18, 91),
        ('corridor', 27.2, 72.0, 580, 15.0, 55.0, 90, 20.0, 2, 70),
        ('A101', 23.6, 54.0, 740, 9.0, 45.0, 85, 48.0, 12, 87),
        ('B201', 22.4, 49.0, 710, 7.5, 50.0, 95, 60.0, 6, 89),
        ('D302', 24.8, 62.0, 850, 12.0, 56.0, 115, 50.0, 10, 78)
    ]
    cur.executemany("INSERT OR IGNORE INTO room_telemetry (room_id, temperature, humidity, co2, pm25, noise_level, tvoc, occupancy, tables_available, comfort_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", telemetry)

    # Seed Default Equipment
    equipment = [
        ('lib2', 'Daikin Central Chiller Loop V1', 'HVAC-LIB-01', 'HVAC', 'Operational'),
        ('lib2', 'Silent Reading Pod Array (x12)', 'FURN-LIB-02', 'Furniture', 'Operational'),
        ('canteen', 'Heavy-Duty Commercial Exhaust #1', 'EXH-CAN-01', 'HVAC', 'Needs Inspection'),
        ('gedungD', 'Inverter Split AC 2.5HP (Unit B)', 'AC-GDD-02', 'HVAC', 'Needs Inspection'),
        ('A101', 'Sony Laser Projector 4K 5000 Lumens', 'PRJ-A101-01', 'Audio-Visual', 'Broken'),
        ('B201', 'Apple M2 iMac Workstations (x35)', 'LAB-B201-PC', 'Computer Lab', 'Operational')
    ]
    cur.executemany("INSERT OR IGNORE INTO room_equipment (room_id, name, serial_number, category, status) VALUES (?, ?, ?, ?, ?)", equipment)

    # Seed Default Reports
    reports = [
        ('#R-101', 'A101', 1, 'Nasira Siddiqa', 'student', 'Audio-Visual', 'Projector Bulb Dead', 'Projector turns on but lamp flashes red and does not project slides.', 'HIGH', 'In Progress', 'Assigned to Audio Visual team. Bulb replacement scheduled.'),
        ('#R-102', 'gedungD', 1, 'Kevin Jonathan', 'student', 'HVAC', 'Air Conditioner Leaking Water', 'Daikin cassette unit dripping condensation water directly onto study bench.', 'CRITICAL', 'Critical', 'Emergency technician dispatched to inspect drainage pump.'),
        ('#R-103', 'lib2', 1, 'Alex Tan', 'student', 'Electrical', 'Power Outlets Near Window Unresponsive', 'Row 4 outlets have no electrical current.', 'LOW', 'Resolved', 'Circuit breaker #B2-4 reset by electrical staff.')
    ]
    cur.executemany("INSERT OR IGNORE INTO reports (id, room_id, reporter_id, reporter_name, reporter_role, category, issue, description, priority, status, admin_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", reports)

    # Seed Default Thermal Feedback
    thermal = [
        ('TF-101', 'canteen', 'alex_tan', 'Alex Tan', 'extremely_hot', 26.8, 68.0),
        ('TF-102', 'canteen', 'kevin_j', 'Kevin Jonathan', 'hot', 26.5, 67.0),
        ('TF-103', 'lib2', 'nasira', 'Nasira Siddiqa', 'comfortable', 22.8, 48.0),
        ('TF-104', 'gedungD', 'budi_s', 'Budi Santoso', 'hot', 25.5, 63.0)
    ]
    cur.executemany("INSERT OR IGNORE INTO thermal_feedback (id, room_id, user_id, user_name, rating, temp_snapshot, hum_snapshot) VALUES (?, ?, ?, ?, ?, ?, ?)", thermal)

    # Seed Default Preferences
    cur.execute("INSERT OR IGNORE INTO user_preferences (user_id, music_enabled, music_volume, radar_mode_enabled, default_heatmap_layer, notifications_enabled) VALUES ('student', 0, 40, 1, 'thermal', 1)")
    cur.execute("INSERT OR IGNORE INTO user_preferences (user_id, music_enabled, music_volume, radar_mode_enabled, default_heatmap_layer, notifications_enabled) VALUES ('admin', 0, 40, 1, 'thermal', 1)")

    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Security & Hashing Helpers
# -----------------------------------------------------------------------------
def hash_password(password: str, salt_hex: str = None) -> tuple:
    if not salt_hex:
        salt_hex = os.urandom(16).hex()
    salt_bytes = binascii.unhexlify(salt_hex)
    pwd_bytes = password.encode('utf-8')
    derived = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
    return derived.hex(), salt_hex

def verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    try:
        salt_bytes = binascii.unhexlify(salt_hex)
        derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000).hex()
        return derived == stored_hash
    except Exception:
        return False

def create_session(username: str, role: str) -> str:
    token = "aeris_" + uuid.uuid4().hex
    conn = get_db()
    cur = conn.cursor()
    expires_at = datetime.fromtimestamp(time.time() + 86400 * 7).isoformat()
    cur.execute("INSERT INTO sessions (token, user_id, username, role, expires_at) VALUES (?, ?, ?, ?, ?)",
        (token, username, username, role, expires_at))
    conn.commit()
    conn.close()
    return token

def get_session_user(token: str):
    if not token:
        return None
    token = token.replace("Bearer ", "").strip()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions WHERE token = ? AND datetime(expires_at) > datetime('now')", (token,))
    sess = cur.fetchone()
    if not sess:
        conn.close()
        return None
    cur.execute("SELECT id, username, name, email, role, xp, level_number, student_nim, faculty_dept, avatar_url FROM users WHERE username = ?", (sess["username"],))
    user = cur.fetchone()
    conn.close()
    return dict(user) if user else None

# -----------------------------------------------------------------------------
# Achievement Evaluation Engine
# -----------------------------------------------------------------------------
def check_user_achievements(username: str):
    conn = get_db()
    cur = conn.cursor()

    # User statistics
    cur.execute("SELECT COUNT(*) AS c FROM reports WHERE reporter_name LIKE ? OR reporter_id IN (SELECT id FROM users WHERE username = ?)", (f"%{username}%", username))
    reports_submitted = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM reports WHERE (reporter_name LIKE ? OR reporter_id IN (SELECT id FROM users WHERE username = ?)) AND status = 'Resolved'", (f"%{username}%", username))
    reports_resolved = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM thermal_feedback WHERE user_id = ?", (username,))
    thermal_feedback = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM verifications WHERE user_id = ?", (username,))
    verifications = cur.fetchone()["c"]

    cur.execute("SELECT xp FROM users WHERE username = ?", (username,))
    user_row = cur.fetchone()
    current_xp = user_row["xp"] if user_row else 0

    cur.execute("SELECT * FROM achievements")
    all_achievements = cur.fetchall()

    newly_unlocked = []

    for ach in all_achievements:
        metric = ach["target_metric"]
        target = ach["target_count"]
        val = 0
        if metric == "reports_submitted": val = reports_submitted
        elif metric == "reports_resolved": val = reports_resolved
        elif metric == "thermal_feedback": val = thermal_feedback
        elif metric == "verifications": val = verifications
        elif metric == "xp": val = current_xp

        if val >= target:
            cur.execute("SELECT * FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (username, ach["id"]))
            already = cur.fetchone()
            if not already:
                cur.execute("INSERT INTO user_achievements (user_id, achievement_id, notified) VALUES (?, ?, 0)", (username, ach["id"]))
                # Create notification
                notif_id = "NOTIF-" + uuid.uuid4().hex[:8].upper()
                cur.execute("""
                    INSERT INTO notifications (id, user_id, type, title, message, icon, link, is_read)
                    VALUES (?, ?, 'achievement', ?, ?, ?, ?, 0)
                """, (notif_id, username, f"Unlocked: {ach['title']}!", f"Congratulations! You unlocked {ach['title']} ({ach['icon']}). +{ach['xp_reward']} XP earned!", ach['icon'], "user/achievements.html"))
                
                # Award XP
                cur.execute("UPDATE users SET xp = xp + ? WHERE username = ?", (ach["xp_reward"], username))
                newly_unlocked.append(dict(ach))

    conn.commit()
    conn.close()
    return newly_unlocked

# -----------------------------------------------------------------------------
# HTTP Server & RESTful API Handler
# -----------------------------------------------------------------------------
class AerisApiHandler(BaseHTTPRequestHandler):
    server_version = "AERIS-Core/2.1"

    def send_json(self, status_code: int, data: dict):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def get_auth_user(self):
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return get_session_user(auth_header)
        # Check cookie if present
        cookies = self.headers.get('Cookie', '')
        for c in cookies.split(';'):
            c = c.strip()
            if c.startswith('aeris_token='):
                token = c.split('=', 1)[1]
                return get_session_user(token)
        return None

    def read_json_body(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode('utf-8')
            return json.loads(raw)
        except Exception:
            return None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # ---------------------------------------------------------------------
        # API Routes: /api/v1/...
        # ---------------------------------------------------------------------
        if path.startswith("/api/v1/"):
            return self.handle_api_get(path, query)

        # OpenAPI Spec & Swagger Docs shortcuts
        if path == "/api/openapi.json":
            spec_path = os.path.join(BASE_DIR, "api", "openapi.json")
            if os.path.exists(spec_path):
                with open(spec_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
                return
            return self.send_json(404, {"success": False, "message": "OpenAPI spec not found"})

        # Static File Serving
        self.serve_static_file(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/v1/"):
            return self.handle_api_post(path)

        self.send_json(404, {"success": False, "message": "Endpoint not found"})

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/v1/"):
            return self.handle_api_patch(path)

        self.send_json(404, {"success": False, "message": "Endpoint not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/v1/"):
            return self.handle_api_delete(path)

        self.send_json(404, {"success": False, "message": "Endpoint not found"})

    # -------------------------------------------------------------------------
    # API Dispatchers
    # -------------------------------------------------------------------------
    def handle_api_get(self, path: str, query: dict):
        user = self.get_auth_user()

        # 1. Auth Me
        if path == "/api/v1/auth/me":
            if not user:
                return self.send_json(401, {"success": False, "message": "Unauthorized / Session Expired"})
            return self.send_json(200, {"success": True, "data": user})

        # 2. Profile
        if path == "/api/v1/profile":
            u = user if user else {"username": "student", "role": "student"}
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = ?", (u["username"],))
            p = cur.fetchone()
            if not p:
                conn.close()
                return self.send_json(404, {"success": False, "message": "User not found"})
            
            # Aggregate contributions
            cur.execute("SELECT COUNT(*) AS c FROM reports WHERE reporter_name LIKE ? OR reporter_id = ?", (f"%{u['username']}%", p["id"]))
            reports_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM reports WHERE (reporter_name LIKE ? OR reporter_id = ?) AND status = 'Resolved'", (f"%{u['username']}%", p["id"]))
            resolved_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM thermal_feedback WHERE user_id = ?", (u["username"],))
            feedback_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM verifications WHERE user_id = ?", (u["username"],))
            verif_c = cur.fetchone()["c"]
            
            # Achievements count
            cur.execute("SELECT COUNT(*) AS c FROM user_achievements WHERE user_id = ?", (u["username"],))
            ach_c = cur.fetchone()["c"]

            data = dict(p)
            data.pop("password_hash", None)
            data.pop("salt", None)
            data["stats"] = {
                "totalReports": reports_c,
                "resolvedReports": resolved_c,
                "totalFeedbacks": feedback_c,
                "totalVerifications": verif_c,
                "unlockedAchievements": ach_c
            }
            conn.close()
            return self.send_json(200, {"success": True, "data": data})

        # 3. Achievements List
        if path == "/api/v1/achievements":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM achievements ORDER BY xp_reward ASC")
            achievements = [dict(r) for r in cur.fetchall()]
            conn.close()
            return self.send_json(200, {"success": True, "data": achievements})

        # 4. User Unlocked Achievements
        if path == "/api/v1/achievements/my":
            target_user = user["username"] if user else (query.get("user", ["student"])[0])
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT a.*, ua.unlocked_at, ua.notified 
                FROM achievements a
                JOIN user_achievements ua ON a.id = ua.achievement_id
                WHERE ua.user_id = ?
                ORDER BY ua.unlocked_at DESC
            """, (target_user,))
            unlocked = [dict(r) for r in cur.fetchall()]
            conn.close()
            return self.send_json(200, {"success": True, "data": unlocked})

        # 5. Achievements Progress
        if path == "/api/v1/achievements/progress":
            target_user = user["username"] if user else (query.get("user", ["student"])[0])
            conn = get_db()
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) AS c FROM reports WHERE reporter_name LIKE ?", (f"%{target_user}%",))
            rep_sub = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM reports WHERE reporter_name LIKE ? AND status = 'Resolved'", (f"%{target_user}%",))
            rep_res = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM thermal_feedback WHERE user_id = ?", (target_user,))
            therm_fb = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM verifications WHERE user_id = ?", (target_user,))
            verifs = cur.fetchone()["c"]
            cur.execute("SELECT xp FROM users WHERE username = ?", (target_user,))
            xp_row = cur.fetchone()
            current_xp = xp_row["xp"] if xp_row else 0

            cur.execute("""
                SELECT a.*, ua.unlocked_at 
                FROM achievements a
                LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
                ORDER BY a.xp_reward ASC
            """, (target_user,))
            rows = cur.fetchall()
            
            res = []
            for r in rows:
                d = dict(r)
                m = d["target_metric"]
                cur_val = 0
                if m == "reports_submitted": cur_val = rep_sub
                elif m == "reports_resolved": cur_val = rep_res
                elif m == "thermal_feedback": cur_val = therm_fb
                elif m == "verifications": cur_val = verifs
                elif m == "xp": cur_val = current_xp
                d["current_progress"] = min(cur_val, d["target_count"])
                d["percentage"] = min(100, int((cur_val / d["target_count"]) * 100)) if d["target_count"] > 0 else 100
                d["is_unlocked"] = d["unlocked_at"] is not None
                res.append(d)

            conn.close()
            return self.send_json(200, {"success": True, "data": res})

        # 6. Notifications
        if path == "/api/v1/notifications":
            target_user = user["username"] if user else (query.get("user", ["student"])[0])
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (target_user,))
            items = [dict(r) for r in cur.fetchall()]
            unread_c = sum(1 for item in items if not item["is_read"])
            conn.close()
            return self.send_json(200, {"success": True, "data": {"notifications": items, "unread_count": unread_c}})

        # 7. Locations List
        if path == "/api/v1/locations":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT r.*, t.temperature, t.humidity, t.co2, t.occupancy, t.comfort_score
                FROM rooms r
                LEFT JOIN (
                    SELECT room_id, temperature, humidity, co2, occupancy, comfort_score, MAX(recorded_at)
                    FROM room_telemetry GROUP BY room_id
                ) t ON r.id = t.room_id
                ORDER BY r.building, r.floor, r.name
            """)
            rooms = [dict(r) for r in cur.fetchall()]
            conn.close()
            return self.send_json(200, {"success": True, "data": rooms})

        # 8. Single Location Detail
        if path.startswith("/api/v1/locations/"):
            room_id = path.replace("/api/v1/locations/", "").strip()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM rooms WHERE id = ? OR room_code = ?", (room_id, room_id))
            room = cur.fetchone()
            if not room:
                conn.close()
                return self.send_json(404, {"success": False, "message": f"Room '{room_id}' not found"})
            
            # Telemetry
            cur.execute("SELECT * FROM room_telemetry WHERE room_id = ? ORDER BY recorded_at DESC LIMIT 1", (room["id"],))
            telem = cur.fetchone()
            # Equipment
            cur.execute("SELECT * FROM room_equipment WHERE room_id = ?", (room["id"],))
            equip = [dict(e) for e in cur.fetchall()]
            # Recent reports
            cur.execute("SELECT * FROM reports WHERE room_id = ? ORDER BY created_at DESC LIMIT 10", (room["id"],))
            reps = [dict(rp) for rp in cur.fetchall()]
            # Feedback
            cur.execute("SELECT * FROM thermal_feedback WHERE room_id = ? ORDER BY created_at DESC LIMIT 20", (room["id"],))
            fbs = [dict(f) for f in cur.fetchall()]

            data = dict(room)
            data["telemetry"] = dict(telem) if telem else None
            data["equipment"] = equip
            data["reports"] = reps
            data["recent_feedback"] = fbs
            conn.close()
            return self.send_json(200, {"success": True, "data": data})

        # 9. Environmental Radar Summary
        if path == "/api/v1/environment/radar":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id, name, building, floor FROM rooms")
            rooms = cur.fetchall()
            radar_data = []
            for r in rooms:
                cur.execute("SELECT rating, created_at FROM thermal_feedback WHERE room_id = ? ORDER BY created_at DESC LIMIT 30", (r["id"],))
                fbs = cur.fetchall()
                cur.execute("SELECT temperature, humidity, co2 FROM room_telemetry WHERE room_id = ? ORDER BY recorded_at DESC LIMIT 1", (r["id"],))
                tel = cur.fetchone()
                
                counts = {"extremely_hot": 0, "hot": 0, "comfortable": 0, "cool": 0, "cold": 0}
                for f in fbs:
                    if f["rating"] in counts: counts[f["rating"]] += 1
                total = len(fbs)
                comfort_pct = int((counts["comfortable"] / total) * 100) if total > 0 else 80
                
                category = "GREEN"
                if counts["extremely_hot"] > 0: category = "RED"
                elif counts["hot"] >= counts["comfortable"]: category = "ORANGE"
                elif counts["cool"] + counts["cold"] >= counts["comfortable"]: category = "BLUE"
                elif total == 0: category = "GREEN"

                radar_data.append({
                    "roomId": r["id"],
                    "roomName": r["name"],
                    "building": r["building"],
                    "radarCategory": category,
                    "comfortPercentage": comfort_pct,
                    "feedbackCount": total,
                    "sensorTelemetry": {
                        "temperature": tel["temperature"] if tel else 23.0,
                        "humidity": tel["humidity"] if tel else 50.0,
                        "co2": tel["co2"] if tel else 600
                    }
                })
            conn.close()
            return self.send_json(200, {"success": True, "data": radar_data})

        # 10. Reports List
        if path == "/api/v1/reports":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM reports ORDER BY created_at DESC")
            reps = [dict(r) for r in cur.fetchall()]
            conn.close()
            return self.send_json(200, {"success": True, "data": reps})

        # 11. Single Report Detail
        if path.startswith("/api/v1/reports/"):
            rep_id = path.replace("/api/v1/reports/", "").strip()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM reports WHERE id = ?", (rep_id,))
            rep = cur.fetchone()
            if not rep:
                conn.close()
                return self.send_json(404, {"success": False, "message": f"Report '{rep_id}' not found"})
            cur.execute("SELECT * FROM verifications WHERE report_id = ?", (rep_id,))
            verifs = [dict(v) for v in cur.fetchall()]
            data = dict(rep)
            data["verifications"] = verifs
            conn.close()
            return self.send_json(200, {"success": True, "data": data})

        # 12. QR Codes List
        if path == "/api/v1/qr-codes":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id, name, room_code, building, floor, qr_code, qr_active FROM rooms")
            qrs = [dict(r) for r in cur.fetchall()]
            conn.close()
            return self.send_json(200, {"success": True, "data": qrs})

        # 13. Maintenance List
        if path == "/api/v1/maintenance":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM maintenance_tasks ORDER BY created_at DESC")
            tasks = [dict(t) for t in cur.fetchall()]
            cur.execute("SELECT * FROM maintenance_logs ORDER BY logged_at DESC LIMIT 50")
            logs = [dict(l) for l in cur.fetchall()]
            conn.close()
            return self.send_json(200, {"success": True, "data": {"tasks": tasks, "logs": logs}})

        # 14. Admin Dashboard KPI
        if path == "/api/v1/admin/dashboard":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM reports WHERE priority = 'CRITICAL' AND status != 'Resolved'")
            crit_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM reports WHERE priority IN ('HIGH', 'MEDIUM') AND status != 'Resolved'")
            warn_c = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM rooms")
            rooms_c = cur.fetchone()["c"]
            cur.execute("SELECT AVG(comfort_score) AS avg_s FROM room_telemetry")
            avg_row = cur.fetchone()
            avg_score = int(avg_row["avg_s"]) if avg_row and avg_row["avg_s"] else 84
            conn.close()
            return self.send_json(200, {"success": True, "data": {
                "criticalEmergencies": crit_c,
                "needsAttention": warn_c,
                "monitoredZones": rooms_c,
                "avgCampusComfort": avg_score
            }})

        # 15. User Preferences
        if path == "/api/v1/preferences":
            u = user["username"] if user else "student"
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM user_preferences WHERE user_id = ?", (u,))
            pref = cur.fetchone()
            conn.close()
            if not pref:
                return self.send_json(200, {"success": True, "data": {"music_enabled": False, "music_volume": 40, "radar_mode_enabled": True}})
            return self.send_json(200, {"success": True, "data": dict(pref)})

        return self.send_json(404, {"success": False, "message": f"Resource not found: {path}"})

    # -------------------------------------------------------------------------
    # API POST Handler
    # -------------------------------------------------------------------------
    def handle_api_post(self, path: str):
        payload = self.read_json_body()
        if payload is None:
            return self.send_json(400, {"success": False, "message": "Invalid JSON payload"})

        # 1. Login
        if path == "/api/v1/auth/login":
            username = payload.get("username", "").strip()
            password = payload.get("password", "").strip()
            if not username or not password:
                return self.send_json(400, {"success": False, "message": "Username and password required"})
            
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
            u = cur.fetchone()
            conn.close()

            if not u:
                return self.send_json(401, {"success": False, "message": "Invalid credentials"})
            
            # Verify password
            is_valid = verify_password(password, u["password_hash"], u["salt"])
            # Fallback for plain demo
            if not is_valid and password == "password":
                is_valid = True

            if not is_valid:
                return self.send_json(401, {"success": False, "message": "Invalid password"})

            token = create_session(u["username"], u["role"])
            user_data = dict(u)
            user_data.pop("password_hash", None)
            user_data.pop("salt", None)
            return self.send_json(200, {"success": True, "message": "Authenticated successfully", "token": token, "data": user_data})

        # 2. Register
        if path == "/api/v1/auth/register":
            username = payload.get("username", "").strip().lower()
            password = payload.get("password", "").strip()
            name = payload.get("name", "").strip()
            role = payload.get("role", "student").strip()
            email = payload.get("email", f"{username}@umn.ac.id").strip()

            if not username or not password or len(password) < 4:
                return self.send_json(400, {"success": False, "message": "Valid username and password (min 4 chars) required"})

            pwd_hash, salt = hash_password(password)
            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO users (username, name, email, role, password_hash, salt, xp, level_number)
                    VALUES (?, ?, ?, ?, ?, ?, 50, 1)
                """, (username, name or username.title(), email, role, pwd_hash, salt))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return self.send_json(409, {"success": False, "message": "Username or email already registered"})
            conn.close()

            token = create_session(username, role)
            return self.send_json(201, {"success": True, "message": "User registered successfully", "token": token})

        # 3. Logout
        if path == "/api/v1/auth/logout":
            auth_header = self.headers.get('Authorization', '')
            token = auth_header.replace('Bearer ', '').strip()
            if token:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                conn.close()
            return self.send_json(200, {"success": True, "message": "Logged out successfully"})

        # 4. Avatar Upload
        if path == "/api/v1/profile/avatar":
            user = self.get_auth_user()
            if not user:
                # Fallback to demo student if not authenticated
                user = {"username": "student"}

            image_data = payload.get("image", "")
            if not image_data or not isinstance(image_data, str):
                return self.send_json(400, {"success": False, "message": "No image data provided"})

            # Validate base64 image data
            mime = "image/png"
            if "," in image_data:
                header, raw_b64 = image_data.split(",", 1)
                if "image/jpeg" in header or "image/jpg" in header: mime = "image/jpeg"
                elif "image/webp" in header: mime = "image/webp"
                elif "image/png" in header: mime = "image/png"
                else:
                    return self.send_json(400, {"success": False, "message": "Unsupported format. Use JPG, PNG, or WebP."})
            else:
                raw_b64 = image_data

            try:
                decoded = base64.b64decode(raw_b64)
            except Exception:
                return self.send_json(400, {"success": False, "message": "Invalid base64 encoding"})

            if len(decoded) > 2 * 1024 * 1024:
                return self.send_json(400, {"success": False, "message": "File size exceeds 2MB maximum limit"})

            ext = "png" if mime == "image/png" else ("webp" if mime == "image/webp" else "jpg")
            filename = f"avatar_{user['username']}_{int(time.time())}.{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Clean previous avatar file if exists
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT avatar_url FROM users WHERE username = ?", (user["username"],))
            old_row = cur.fetchone()
            if old_row and old_row["avatar_url"] and not old_row["avatar_url"].startswith("data:"):
                old_path = os.path.join(BASE_DIR, old_row["avatar_url"].lstrip("/"))
                if os.path.exists(old_path) and os.path.commonpath([old_path, UPLOAD_DIR]) == UPLOAD_DIR:
                    try: os.remove(old_path)
                    except Exception: pass

            # Save new file
            with open(file_path, "wb") as f:
                f.write(decoded)

            rel_url = f"uploads/avatars/{filename}"
            cur.execute("UPDATE users SET avatar_url = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?", (rel_url, user["username"]))
            conn.commit()
            conn.close()

            return self.send_json(200, {
                "success": True,
                "message": "Profile picture updated successfully",
                "data": {"avatar_url": rel_url}
            })

        # 5. Environmental Feedback
        if path == "/api/v1/environment/feedback":
            user = self.get_auth_user()
            user_id = user["username"] if user else payload.get("userId", "student")
            user_name = user["name"] if user else payload.get("userName", "Student")

            room_id = payload.get("roomId", "").strip()
            rating = payload.get("rating", "").strip()

            if not room_id or rating not in ['extremely_hot', 'hot', 'comfortable', 'cool', 'cold']:
                return self.send_json(400, {"success": False, "message": "Valid roomId and rating required"})

            conn = get_db()
            cur = conn.cursor()
            # Cooldown check: 5 minutes
            cur.execute("""
                SELECT * FROM thermal_feedback 
                WHERE room_id = ? AND user_id = ? AND datetime(created_at) > datetime('now', '-5 minutes')
            """, (room_id, user_id))
            if cur.fetchone():
                conn.close()
                return self.send_json(429, {"success": False, "message": "Cooldown active: you already rated this room recently. Thank you!"})

            fb_id = "TF-" + uuid.uuid4().hex[:8].upper()
            cur.execute("""
                INSERT INTO thermal_feedback (id, room_id, user_id, user_name, rating, temp_snapshot, hum_snapshot)
                VALUES (?, ?, ?, ?, ?, 23.5, 52.0)
            """, (fb_id, room_id, user_id, user_name, rating))
            conn.commit()
            conn.close()

            # Check achievements
            unlocked = check_user_achievements(user_id)

            return self.send_json(201, {
                "success": True,
                "message": "Thermal feedback recorded successfully",
                "data": {"feedback_id": fb_id, "rating": rating, "new_achievements": unlocked}
            })

        # 6. Create Report
        if path == "/api/v1/reports":
            user = self.get_auth_user()
            user_id = user["username"] if user else payload.get("reporter_username", "student")
            name = user["name"] if user else payload.get("reporter_name", "Student")

            room_id = payload.get("roomId", "").strip()
            category = payload.get("category", "General").strip()
            issue = payload.get("issue", "").strip()
            desc = payload.get("description", "").strip()
            priority = payload.get("priority", "MEDIUM").strip().upper()
            photo = payload.get("photo", None)

            if not room_id or not issue:
                return self.send_json(400, {"success": False, "message": "Room and issue title required"})

            report_id = "R-" + uuid.uuid4().hex[:6].upper()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO reports (id, room_id, reporter_name, reporter_role, category, issue, description, priority, status, photo_url)
                VALUES (?, ?, ?, 'student', ?, ?, ?, ?, 'Submitted', ?)
            """, (report_id, room_id, name, category, issue, desc, priority, photo))

            # Add to maintenance log
            log_id = "LOG-" + uuid.uuid4().hex[:6].upper()
            cur.execute("""
                INSERT INTO maintenance_logs (id, room_id, room_name, report_id, event_type, title, description, actor, actor_role, badge)
                VALUES (?, ?, ?, ?, 'report_created', ?, ?, ?, 'Student', 'New Report')
            """, (log_id, room_id, room_id, report_id, f"Report Submitted: {issue}", desc, name))

            # Reward XP
            cur.execute("UPDATE users SET xp = xp + 50 WHERE username = ?", (user_id,))
            conn.commit()
            conn.close()

            # Check achievements
            unlocked = check_user_achievements(user_id)

            return self.send_json(201, {
                "success": True,
                "message": "Facility report submitted successfully",
                "data": {"report_id": report_id, "new_achievements": unlocked}
            })

        # 7. Create Verification
        if path.startswith("/api/v1/reports/") and path.endswith("/verify"):
            report_id = path.replace("/api/v1/reports/", "").replace("/verify", "").strip()
            user = self.get_auth_user()
            user_id = user["username"] if user else payload.get("userId", "student")
            user_name = user["name"] if user else payload.get("userName", "Student")
            response = payload.get("response", "still_exists")

            conn = get_db()
            cur = conn.cursor()
            # Prevent double voting
            cur.execute("SELECT * FROM verifications WHERE report_id = ? AND user_id = ?", (report_id, user_id))
            if cur.fetchone():
                conn.close()
                return self.send_json(409, {"success": False, "message": "You have already verified this incident report"})

            cur.execute("SELECT room_id FROM reports WHERE id = ?", (report_id,))
            rep = cur.fetchone()
            room_id = rep["room_id"] if rep else "lib2"

            cur.execute("""
                INSERT INTO verifications (report_id, room_id, user_id, user_name, response)
                VALUES (?, ?, ?, ?, ?)
            """, (report_id, room_id, user_id, user_name, response))
            cur.execute("UPDATE users SET xp = xp + 25 WHERE username = ?", (user_id,))
            conn.commit()
            conn.close()

            unlocked = check_user_achievements(user_id)
            return self.send_json(201, {
                "success": True,
                "message": "Verification submitted successfully",
                "data": {"report_id": report_id, "response": response, "new_achievements": unlocked}
            })

        # 8. Create Maintenance Work Order
        if path == "/api/v1/maintenance":
            title = payload.get("title", "").strip()
            room_id = payload.get("roomId", "").strip()
            assigned = payload.get("assignedTo", "HVAC Team").strip()
            priority = payload.get("priority", "MEDIUM").strip()
            cat = payload.get("category", "General").strip()

            if not title or not room_id:
                return self.send_json(400, {"success": False, "message": "Task title and roomId required"})

            task_id = "TASK-" + uuid.uuid4().hex[:6].upper()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO maintenance_tasks (id, room_id, title, category, priority, status, assigned_to)
                VALUES (?, ?, ?, ?, ?, 'Pending', ?)
            """, (task_id, room_id, title, cat, priority, assigned))
            conn.commit()
            conn.close()

            return self.send_json(201, {"success": True, "message": "Work order created successfully", "data": {"task_id": task_id}})

        # 9. Regenerate QR Code
        if path.startswith("/api/v1/qr-codes/") and path.endswith("/regenerate"):
            room_id = path.replace("/api/v1/qr-codes/", "").replace("/regenerate", "").strip()
            new_code = f"AERIS-ROOM-{room_id.upper()}-{uuid.uuid4().hex[:4].upper()}"
            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE rooms SET qr_code = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_code, room_id))
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "message": f"QR Code regenerated for {room_id}", "data": {"qr_code": new_code}})

        return self.send_json(404, {"success": False, "message": f"Endpoint not found: {path}"})

    # -------------------------------------------------------------------------
    # API PATCH Handler
    # -------------------------------------------------------------------------
    def handle_api_patch(self, path: str):
        payload = self.read_json_body()
        if payload is None:
            return self.send_json(400, {"success": False, "message": "Invalid JSON payload"})

        user = self.get_auth_user()
        target_user = user["username"] if user else "student"

        # 1. Mark All Notifications as Read
        if path == "/api/v1/notifications/read-all":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (target_user,))
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "message": "All notifications marked as read"})

        # 2. Mark Single Notification as Read
        if path.startswith("/api/v1/notifications/") and path.endswith("/read"):
            notif_id = path.replace("/api/v1/notifications/", "").replace("/read", "").strip()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "message": f"Notification {notif_id} marked as read"})

        # 3. Update Preferences
        if path == "/api/v1/preferences":
            conn = get_db()
            cur = conn.cursor()
            music = 1 if payload.get("music_enabled", False) else 0
            vol = int(payload.get("music_volume", 40))
            radar = 1 if payload.get("radar_mode_enabled", True) else 0
            layer = payload.get("default_heatmap_layer", "thermal")

            cur.execute("""
                INSERT INTO user_preferences (user_id, music_enabled, music_volume, radar_mode_enabled, default_heatmap_layer)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    music_enabled = excluded.music_enabled,
                    music_volume = excluded.music_volume,
                    radar_mode_enabled = excluded.radar_mode_enabled,
                    default_heatmap_layer = excluded.default_heatmap_layer,
                    updated_at = CURRENT_TIMESTAMP
            """, (target_user, music, vol, radar, layer))
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "message": "Preferences updated successfully"})

        # 4. Toggle QR Code Active State
        if path.startswith("/api/v1/qr-codes/") and path.endswith("/toggle"):
            room_id = path.replace("/api/v1/qr-codes/", "").replace("/toggle", "").strip()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE rooms SET qr_active = CASE WHEN qr_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (room_id,))
            cur.execute("SELECT qr_active FROM rooms WHERE id = ?", (room_id,))
            row = cur.fetchone()
            conn.commit()
            conn.close()
            is_active = bool(row["qr_active"]) if row else True
            return self.send_json(200, {"success": True, "message": f"QR Code for {room_id} status toggled", "data": {"qr_active": is_active}})

        # 5. Update Report Status / Notes
        if path.startswith("/api/v1/reports/"):
            rep_id = path.replace("/api/v1/reports/", "").strip()
            conn = get_db()
            cur = conn.cursor()
            status = payload.get("status")
            notes = payload.get("admin_notes")

            updates = []
            vals = []
            if status:
                updates.append("status = ?")
                vals.append(status)
            if notes:
                updates.append("admin_notes = ?")
                vals.append(notes)

            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                vals.append(rep_id)
                cur.execute(f"UPDATE reports SET {', '.join(updates)} WHERE id = ?", vals)
                conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "message": f"Report {rep_id} updated"})

        return self.send_json(404, {"success": False, "message": f"Endpoint not found: {path}"})

    # -------------------------------------------------------------------------
    # API DELETE Handler
    # -------------------------------------------------------------------------
    def handle_api_delete(self, path: str):
        user = self.get_auth_user()
        target_user = user["username"] if user else "student"

        # Delete Avatar
        if path == "/api/v1/profile/avatar":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT avatar_url FROM users WHERE username = ?", (target_user,))
            row = cur.fetchone()
            if row and row["avatar_url"]:
                file_path = os.path.join(BASE_DIR, row["avatar_url"].lstrip("/"))
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except Exception: pass
            cur.execute("UPDATE users SET avatar_url = NULL, updated_at = CURRENT_TIMESTAMP WHERE username = ?", (target_user,))
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "message": "Profile picture removed successfully"})

        return self.send_json(404, {"success": False, "message": f"Endpoint not found: {path}"})

    # -------------------------------------------------------------------------
    # Static File Server
    # -------------------------------------------------------------------------
    def serve_static_file(self, req_path: str):
        clean_path = req_path.lstrip("/")
        if not clean_path or clean_path == "":
            clean_path = "index.html"
        
        # Prevent directory traversal
        full_path = os.path.normpath(os.path.join(BASE_DIR, clean_path))
        if not full_path.startswith(BASE_DIR):
            self.send_error(403, "Access Denied")
            return

        if os.path.isdir(full_path):
            index_candidate = os.path.join(full_path, "index.html")
            if os.path.exists(index_candidate):
                full_path = index_candidate
            else:
                self.send_error(404, "Directory Not Found")
                return

        if not os.path.exists(full_path):
            self.send_error(404, f"File Not Found: {clean_path}")
            return

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            if full_path.endswith(".gltf"): mime_type = "model/gltf+json"
            elif full_path.endswith(".svg"): mime_type = "image/svg+xml"
            elif full_path.endswith(".json"): mime_type = "application/json"
            elif full_path.endswith(".webp"): mime_type = "image/webp"
            elif full_path.endswith(".mp3"): mime_type = "audio/mpeg"
            else: mime_type = "application/octet-stream"

        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {str(e)}")

# -----------------------------------------------------------------------------
# Server Entry Point
# -----------------------------------------------------------------------------
def run(port=PORT):
    init_db()
    server_address = ('', port)
    httpd = HTTPServer(server_address, AerisApiHandler)
    print("=" * 70)
    print(f"🚀 AERIS 2.1 Server listening at http://localhost:{port}")
    print(f"📡 RESTful API Base: http://localhost:{port}/api/v1/")
    print(f"📖 OpenAPI Swagger Docs: http://localhost:{port}/api/docs/")
    print(f"🗄️ Database Initialized: {DB_PATH}")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    p = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        p = int(sys.argv[1])
    run(p)
