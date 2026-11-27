-- ============================================================================
-- AERIS 2.1 - CAMPUS FACILITY MANAGEMENT & ENVIRONMENTAL RADAR PLATFORM
-- Relational Database Schema & Migration Script
-- Compatible with PostgreSQL 13+ and MySQL 8.0+
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. USERS & AUTHENTICATION
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    email VARCHAR(128) UNIQUE NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin', 'technician', 'faculty')),
    password_hash VARCHAR(255) NOT NULL,     -- 100k-iteration PBKDF2 SHA-256 Hash
    salt VARCHAR(64) NOT NULL,              -- 16-byte random cryptographically secure hex salt
    xp INTEGER NOT NULL DEFAULT 0,
    level_number INTEGER NOT NULL DEFAULT 1,
    student_nim VARCHAR(32) NULL,
    faculty_dept VARCHAR(64) NULL DEFAULT 'Faculty of Engineering & Informatics',
    avatar_url TEXT NULL,                    -- Path to uploaded avatar or base64
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- ----------------------------------------------------------------------------
-- 2. CAMPUS ROOMS & PHYSICAL ZONES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rooms (
    id VARCHAR(32) PRIMARY KEY,             -- e.g. 'lib2', 'canteen', 'A101'
    room_code VARCHAR(32) UNIQUE NOT NULL,  -- e.g. 'LIB-F2', 'SC-C1'
    name VARCHAR(128) NOT NULL,
    building VARCHAR(64) NOT NULL,          -- e.g. 'Library', 'Student Center', 'Gedung B'
    floor INTEGER NOT NULL DEFAULT 1,
    room_type VARCHAR(64) NOT NULL DEFAULT 'Study Space',
    capacity INTEGER NOT NULL DEFAULT 50,
    walk_time VARCHAR(32) DEFAULT '3 min walk',
    image_url VARCHAR(255) DEFAULT 'assets/library.jpg',
    qr_code VARCHAR(64) UNIQUE NOT NULL,    -- QR identifier encoded on physical door placards
    qr_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rooms_building ON rooms(building);
CREATE INDEX idx_rooms_floor ON rooms(floor);
CREATE INDEX idx_rooms_qr ON rooms(qr_code);

-- ----------------------------------------------------------------------------
-- 3. REAL-TIME PHYSICAL SENSOR TELEMETRY
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS room_telemetry (
    id BIGSERIAL PRIMARY KEY,
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    temperature NUMERIC(4, 1) NOT NULL,     -- In Celsius (e.g. 23.4)
    humidity NUMERIC(4, 1) NOT NULL,        -- Relative Humidity percentage (e.g. 48.0)
    co2 INTEGER NOT NULL,                   -- In parts per million (e.g. 620)
    pm25 NUMERIC(5, 1) DEFAULT 10.0,        -- PM2.5 in ug/m3
    noise_level NUMERIC(4, 1) DEFAULT 45.0, -- In dBA
    tvoc INTEGER DEFAULT 75,                -- Total Volatile Organic Compounds (ppb)
    occupancy NUMERIC(4, 1) NOT NULL DEFAULT 0.0, -- Occupancy percentage (0-100)
    tables_available INTEGER DEFAULT 10,
    comfort_score INTEGER NOT NULL DEFAULT 85,    -- Computed IEQ score (0-100)
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_telemetry_room_time ON room_telemetry(room_id, recorded_at DESC);

-- ----------------------------------------------------------------------------
-- 4. ROOM EQUIPMENT & AMENITIES INVENTORY
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS room_equipment (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,             -- e.g. 'Daikin Split Inverter AC Unit #1'
    serial_number VARCHAR(64) NULL,
    category VARCHAR(64) NOT NULL,          -- 'HVAC', 'Audio-Visual', 'Furniture', 'Electrical'
    status VARCHAR(32) NOT NULL DEFAULT 'Operational' CHECK (status IN ('Operational', 'Needs Inspection', 'Under Maintenance', 'Broken')),
    installed_at DATE NULL,
    last_inspected_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE INDEX idx_equipment_room ON room_equipment(room_id);

-- ----------------------------------------------------------------------------
-- 5. INCIDENT REPORTS & EMERGENCY DISPATCH
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(32) PRIMARY KEY,             -- e.g. '#R-101'
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    reporter_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    reporter_name VARCHAR(128) NOT NULL,
    reporter_role VARCHAR(32) NOT NULL DEFAULT 'student',
    category VARCHAR(64) NOT NULL CHECK (category IN ('HVAC', 'Air Conditioning', 'Electrical', 'Audio-Visual', 'Equipment', 'Furniture', 'Cleanliness', 'Plumbing', 'Safety', 'General')),
    issue VARCHAR(255) NOT NULL,
    description TEXT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(32) NOT NULL DEFAULT 'Submitted' CHECK (status IN ('Submitted', 'Under Review', 'In Progress', 'Resolved', 'Rejected', 'Critical')),
    photo_url TEXT NULL,                    -- Base64 data or S3 object URI
    admin_notes TEXT NULL,
    technician_notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE INDEX idx_reports_room ON reports(room_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_priority ON reports(priority);
CREATE INDEX idx_reports_category ON reports(category);
CREATE INDEX idx_reports_created ON reports(created_at DESC);

-- ----------------------------------------------------------------------------
-- 6. SMART COMMUNITY CROWDSOURCED VERIFICATIONS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verifications (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(32) NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,           -- Username or user identifier
    user_name VARCHAR(128) NOT NULL,
    response VARCHAR(32) NOT NULL CHECK (response IN ('still_exists', 'fixed')),
    verified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_verifications_report ON verifications(report_id);
CREATE INDEX idx_verifications_user ON verifications(user_id, verified_at DESC);

-- ----------------------------------------------------------------------------
-- 7. FAST COMMUNITY THERMAL COMFORT RADAR FEEDBACK
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS thermal_feedback (
    id VARCHAR(32) PRIMARY KEY,             -- e.g. 'TF-101'
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL,
    user_name VARCHAR(128) NOT NULL,
    rating VARCHAR(32) NOT NULL CHECK (rating IN ('extremely_hot', 'hot', 'comfortable', 'cool', 'cold')),
    temp_snapshot NUMERIC(4, 1) NULL,       -- Sensor reading at time of feedback
    hum_snapshot NUMERIC(4, 1) NULL,        -- Actual humidity at time of feedback
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_thermal_room_time ON thermal_feedback(room_id, created_at DESC);

-- ----------------------------------------------------------------------------
-- 8. FACILITY OPS WORK ORDERS & MAINTENANCE TASKS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_tasks (
    id VARCHAR(32) PRIMARY KEY,             -- e.g. 'TASK-101'
    report_id VARCHAR(32) NULL REFERENCES reports(id) ON DELETE SET NULL,
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    category VARCHAR(64) NOT NULL DEFAULT 'Facility Maintenance',
    priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(32) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Assigned', 'In Progress', 'On Hold', 'Completed', 'Cancelled')),
    assigned_to VARCHAR(128) NOT NULL,
    created_by VARCHAR(64) DEFAULT 'Facility Admin',
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expected_completion TIMESTAMP WITH TIME ZONE NULL,
    completion_date TIMESTAMP WITH TIME ZONE NULL,
    resolution_photo TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_status ON maintenance_tasks(status);
CREATE INDEX idx_tasks_room ON maintenance_tasks(room_id);

-- ----------------------------------------------------------------------------
-- 9. MAINTENANCE TIMELINE AUDIT TRAIL LOGS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_logs (
    id VARCHAR(32) PRIMARY KEY,             -- e.g. 'LOG-001'
    room_id VARCHAR(32) NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    room_name VARCHAR(128) NOT NULL,
    report_id VARCHAR(32) NULL REFERENCES reports(id) ON DELETE SET NULL,
    task_id VARCHAR(32) NULL REFERENCES maintenance_tasks(id) ON DELETE SET NULL,
    event_type VARCHAR(64) NOT NULL,        -- 'report_created', 'verification', 'assigned', 'status_change'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    actor VARCHAR(128) NOT NULL,
    actor_role VARCHAR(32) NOT NULL,
    badge VARCHAR(64) DEFAULT 'Update',
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logs_room_time ON maintenance_logs(room_id, logged_at DESC);

-- ----------------------------------------------------------------------------
-- 10. RECURRING ISSUE DETECTION VIEW (AUTOMATED FLAGGER)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_recurring_issues AS
SELECT 
    r.room_id,
    rm.name AS room_name,
    rm.building,
    r.category,
    COUNT(r.id) AS report_count,
    MAX(r.created_at) AS latest_incident,
    CASE 
        WHEN COUNT(r.id) >= 3 THEN 'CRITICAL_RECURRING'
        ELSE 'WARNING_RECURRING'
    END AS severity
FROM reports r
JOIN rooms rm ON r.room_id = rm.id
WHERE r.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY r.room_id, rm.name, rm.building, r.category
HAVING COUNT(r.id) >= 2;

-- ----------------------------------------------------------------------------
-- 11. ACHIEVEMENTS & GAMIFICATION DEFINITIONS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(32) PRIMARY KEY,             -- e.g. 'first_step', 'active_reporter'
    title VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(64) NOT NULL,          -- 'Reporting', 'Environmental Comfort', 'Verification', 'Milestone'
    icon VARCHAR(16) NOT NULL,              -- Emoji/Symbol e.g. '🌱', '📝'
    target_metric VARCHAR(64) NOT NULL,     -- 'reports_submitted', 'reports_resolved', 'thermal_feedback', 'verifications', 'xp'
    target_count INTEGER NOT NULL,
    xp_reward INTEGER NOT NULL DEFAULT 50,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 12. USER ACHIEVEMENTS UNLOCK RECORD
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    achievement_id VARCHAR(32) NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(user_id, achievement_id)
);

CREATE INDEX idx_user_achievements_user ON user_achievements(user_id);

-- ----------------------------------------------------------------------------
-- 13. IN-APP USER NOTIFICATIONS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(32) PRIMARY KEY,             -- e.g. 'NOTIF-101'
    user_id VARCHAR(64) NOT NULL,
    type VARCHAR(32) NOT NULL DEFAULT 'system', -- 'achievement', 'report_update', 'maintenance', 'system'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    icon VARCHAR(16) DEFAULT '🔔',
    link VARCHAR(255) NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notif_user ON notifications(user_id, is_read, created_at DESC);

-- ----------------------------------------------------------------------------
-- 14. USER PREFERENCES (MUSIC, RADAR, HEATMAP)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(64) PRIMARY KEY,
    music_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    music_volume INTEGER NOT NULL DEFAULT 40,
    radar_mode_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    default_heatmap_layer VARCHAR(32) NOT NULL DEFAULT 'thermal',
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 15. INITIAL SEED DATA (UMN CAMPUS DEMO BASELINE)
-- ----------------------------------------------------------------------------

-- A. Users
INSERT INTO users (username, name, email, role, password_hash, salt, xp, level_number, student_nim, avatar_url)
VALUES 
('student', 'Nasira Siddiqa Nurrahman', 'nasira@umn.ac.id', 'student', 'd6067b84419999be3a129ef66d21f8a846f48386f685c4900a0d4c82b9dc3c46', '3023e716499874cb37f884a4ee62ae5b', 425, 2, '00000157334', NULL),
('admin', 'Facility Operations Team', 'facility@umn.ac.id', 'admin', 'd6067b84419999be3a129ef66d21f8a846f48386f685c4900a0d4c82b9dc3c46', '3023e716499874cb37f884a4ee62ae5b', 1850, 4, 'ADMIN-001', NULL)
ON CONFLICT (username) DO NOTHING;

-- B. Campus Rooms
INSERT INTO rooms (id, room_code, name, building, floor, room_type, capacity, walk_time, image_url, qr_code, qr_active)
VALUES
('lib2', 'LIB-F2', 'Library — Floor 2', 'Library', 2, 'Library & Quiet Study', 120, '3 min walk', 'assets/library.jpg', 'AERIS-ROOM-LIB2', TRUE),
('canteen', 'SC-C1', 'Campus Canteen & Food Court', 'Student Center', 1, 'Dining & Social Space', 200, '1 min walk', 'assets/student-lounge.png', 'AERIS-ROOM-CANTEEN', TRUE),
('lounge', 'SC-L1', 'Student Lounge', 'Student Center', 1, 'Student Social Lounge', 80, '5 min walk', 'assets/student-lounge.png', 'AERIS-ROOM-LOUNGE', TRUE),
('gedungD', 'GD-L1', 'Gedung D — Lounge', 'Gedung D', 1, 'Open Study Area', 60, '2 min walk', 'assets/gedung-d-lounge.jpg', 'AERIS-ROOM-GD-L1', TRUE),
('studyHall', 'AC-F3', 'Academic Study Hall', 'Academic', 3, 'Collaborative Workspace', 90, '8 min walk', 'assets/study-hall.jpg', 'AERIS-ROOM-AC-F3', TRUE),
('corridor', 'GB-C1', 'Gedung B Corridor', 'Gedung B', 1, 'Semi-Open Transit Area', 40, '2 min walk', 'assets/gedung-b-corridor.jpg', 'AERIS-ROOM-GB-C1', TRUE),
('A101', 'A101', 'Smart Classroom A101', 'Academic', 1, 'Lecture Classroom', 65, '4 min walk', 'assets/study-hall.jpg', 'AERIS-ROOM-A101', TRUE),
('B201', 'B201', 'Multimedia Design Lab B201', 'Gedung B', 2, 'Computer Laboratory', 45, '4 min walk', 'assets/library.jpg', 'AERIS-ROOM-B201', TRUE),
('D302', 'D302', 'Collaborative Studio D302', 'Gedung D', 3, 'Project Workshop Studio', 50, '6 min walk', 'assets/gedung-d-lounge.jpg', 'AERIS-ROOM-D302', TRUE)
ON CONFLICT (id) DO NOTHING;

-- C. Sample Baseline Incident Reports
INSERT INTO reports (id, room_id, reporter_name, reporter_role, category, issue, description, priority, status, admin_notes)
VALUES
('#R-101', 'A101', 'Nasira Siddiqa', 'student', 'Audio-Visual', 'Projector Bulb Dead', 'Projector turns on but lamp flashes red and does not project slides.', 'HIGH', 'In Progress', 'Assigned to Audio Visual team. Bulb replacement scheduled.'),
('#R-102', 'gedungD', 'Kevin Jonathan', 'student', 'HVAC', 'Air Conditioner Leaking Water', 'Daikin cassette unit dripping condensation water directly onto study bench.', 'CRITICAL', 'Critical', 'Emergency technician dispatched to inspect drainage pump.'),
('#R-103', 'lib2', 'Alex Tan', 'student', 'Electrical', 'Power Outlets Near Window Unresponsive', 'Row 4 outlets have no electrical current.', 'LOW', 'Resolved', 'Circuit breaker #B2-4 reset by electrical staff.')
ON CONFLICT (id) DO NOTHING;

-- D. Master Achievement Definitions
INSERT INTO achievements (id, title, description, category, icon, target_metric, target_count, xp_reward)
VALUES
('first_step', 'First Step', 'Submit your very first verified campus facility report.', 'Reporting', '🌱', 'reports_submitted', 1, 50),
('facility_contributor', 'Facility Contributor', 'Submit 5 valid facility reports to help keep UMN running smoothly.', 'Reporting', '📝', 'reports_submitted', 5, 100),
('active_reporter', 'Active Reporter', 'Submit 10 valid facility incident reports across campus.', 'Reporting', '⚡', 'reports_submitted', 10, 200),
('comfort_scout', 'Comfort Scout', 'Provide 3 thermal comfort ratings to calibrate indoor air quality.', 'Environmental Comfort', '🌡️', 'thermal_feedback', 3, 50),
('community_helper', 'Community Helper', 'Provide 10 valid environmental feedback ratings to calibrate campus HVAC.', 'Environmental Comfort', '👥', 'thermal_feedback', 10, 150),
('problem_solver', 'Problem Solver', 'Have 5 of your submitted facility reports officially resolved.', 'Reporting', '🛠️', 'reports_resolved', 5, 250),
('community_sentinel', 'Community Sentinel', 'Help verify 3 reported facility conditions around campus.', 'Verification', '🛡️', 'verifications', 3, 75),
('verification_hero', 'Verification Hero', 'Complete 10 valid crowdsourced facility issue verifications.', 'Verification', '🏆', 'verifications', 10, 200),
('facility_champion', 'Facility Champion', 'Reach 1,500 XP and achieve Level 4: Master Campus Steward.', 'Milestone', '👑', 'xp', 1500, 500)
ON CONFLICT (id) DO NOTHING;

-- E. Initial Seed Preferences
INSERT INTO user_preferences (user_id, music_enabled, music_volume, radar_mode_enabled, default_heatmap_layer, notifications_enabled)
VALUES
('student', FALSE, 40, TRUE, 'thermal', TRUE),
('admin', FALSE, 40, TRUE, 'thermal', TRUE)
ON CONFLICT (user_id) DO NOTHING;

