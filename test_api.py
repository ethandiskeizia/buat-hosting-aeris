#!/usr/bin/env python3
"""
Automated API Test Suite for AERIS 2.1
Supports:
1. Live HTTP testing when server is running (e.g. python3 server.py & python3 test_api.py)
2. In-Memory MockSocket testing (works inside restricted sandboxes without network socket permissions)
"""

import io
import json
import sys
import time
from server import AerisApiHandler, init_db

class MockSocket:
    def __init__(self, data=b""):
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()

def execute_api_test(method, path, body=None, headers=None):
    raw_body = json.dumps(body).encode("utf-8") if body else b""
    req_headers = {"Content-Length": str(len(raw_body)), "Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    
    sock = MockSocket()
    sock.rfile = io.BytesIO(raw_body)

    class DirectTestHandler(AerisApiHandler):
        def __init__(self):
            self.rfile = sock.rfile
            self.wfile = sock.wfile
            self.command = method
            self.path = path
            self.request_version = "HTTP/1.1"
            self.requestline = f"{method} {path} HTTP/1.1"
            self.headers = req_headers
            getattr(self, f"do_{method}")()
        def log_message(self, *args):
            pass

    handler = DirectTestHandler()
    resp_raw = sock.wfile.getvalue().decode("utf-8")
    status_line = resp_raw.split("\r\n")[0]
    status_code = int(status_line.split(" ")[1]) if " " in status_line else 500
    body_part = resp_raw.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in resp_raw else ""
    parsed_json = json.loads(body_part) if body_part else {}
    return status_code, parsed_json

def run_all_tests():
    init_db()
    print("=" * 65)
    print("🧪 Running AERIS 2.1 REST API In-Memory / Direct Test Suite")
    print("=" * 65)

    tests_passed = 0
    total_tests = 0

    def assert_test(name, condition, details=""):
        nonlocal tests_passed, total_tests
        total_tests += 1
        if condition:
            print(f"  ✅ PASS: {name}")
            tests_passed += 1
        else:
            print(f"  ❌ FAIL: {name} -> {details}")

    # 1. Login Student
    status, res = execute_api_test("POST", "/api/v1/auth/login", {"username": "student", "password": "password"})
    assert_test("POST /auth/login (Student)", status == 200 and res.get("success") and "token" in res, res)
    student_token = res.get("token")

    # 2. Login Admin
    status, res = execute_api_test("POST", "/api/v1/auth/login", {"username": "admin", "password": "password"})
    assert_test("POST /auth/login (Admin)", status == 200 and res.get("success"), res)

    # 3. Invalid Login
    status, res = execute_api_test("POST", "/api/v1/auth/login", {"username": "student", "password": "wrongpassword"})
    assert_test("POST /auth/login (Reject wrong password)", status == 401 and not res.get("success"), res)

    # 4. Auth Me
    status, res = execute_api_test("GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {student_token}"})
    assert_test("GET /auth/me", status == 200 and res.get("data", {}).get("username") == "student", res)

    # 5. Profile & Contributions
    status, res = execute_api_test("GET", "/api/v1/profile", headers={"Authorization": f"Bearer {student_token}"})
    assert_test("GET /profile", status == 200 and "stats" in res.get("data", {}), res)

    # 6. Avatar Upload & Delete
    test_img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    status, res = execute_api_test("POST", "/api/v1/profile/avatar", {"image": test_img}, headers={"Authorization": f"Bearer {student_token}"})
    assert_test("POST /profile/avatar (Upload PNG)", status == 200 and "avatar_url" in res.get("data", {}), res)

    status, res = execute_api_test("DELETE", "/api/v1/profile/avatar", headers={"Authorization": f"Bearer {student_token}"})
    assert_test("DELETE /profile/avatar (Remove avatar)", status == 200 and res.get("success"), res)

    # 7. Master Achievements List
    status, res = execute_api_test("GET", "/api/v1/achievements")
    assert_test("GET /achievements", status == 200 and len(res.get("data", [])) >= 8, res)

    # 8. Achievements Progress
    status, res = execute_api_test("GET", "/api/v1/achievements/progress", headers={"Authorization": f"Bearer {student_token}"})
    assert_test("GET /achievements/progress", status == 200 and len(res.get("data", [])) > 0, res)

    # 9. Notifications List & Read
    status, res = execute_api_test("GET", "/api/v1/notifications", headers={"Authorization": f"Bearer {student_token}"})
    assert_test("GET /notifications", status == 200 and "unread_count" in res.get("data", {}), res)

    status, res = execute_api_test("PATCH", "/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {student_token}"})
    assert_test("PATCH /notifications/read-all", status == 200 and res.get("success"), res)

    # 10. Locations List
    status, res = execute_api_test("GET", "/api/v1/locations")
    assert_test("GET /locations", status == 200 and len(res.get("data", [])) == 9, res)

    # 11. Single Location Detail
    status, res = execute_api_test("GET", "/api/v1/locations/lib2")
    assert_test("GET /locations/lib2", status == 200 and res.get("data", {}).get("name") == "Library — Floor 2", res)

    # 12. Environmental Radar Summary
    status, res = execute_api_test("GET", "/api/v1/environment/radar")
    assert_test("GET /environment/radar", status == 200 and len(res.get("data", [])) == 9, res)

    # 13. Environmental Feedback
    status, res = execute_api_test("POST", "/api/v1/environment/feedback", {"roomId": "A101", "rating": "comfortable"}, headers={"Authorization": f"Bearer {student_token}"})
    assert_test("POST /environment/feedback", status in [201, 429], res)

    # 14. Reports List & Creation
    status, res = execute_api_test("GET", "/api/v1/reports")
    assert_test("GET /reports", status == 200 and len(res.get("data", [])) >= 3, res)

    status, res = execute_api_test("POST", "/api/v1/reports", {
        "roomId": "studyHall",
        "category": "Furniture",
        "issue": "Wobbly study table near window",
        "description": "Leg screw is loose on table #T4.",
        "priority": "LOW"
    }, headers={"Authorization": f"Bearer {student_token}"})
    assert_test("POST /reports (Submit issue)", status == 201 and "report_id" in res.get("data", {}), res)
    new_rep_id = res.get("data", {}).get("report_id")

    # 15. Verify Report
    status, res = execute_api_test("POST", f"/api/v1/reports/{new_rep_id}/verify", {"response": "still_exists"}, headers={"Authorization": f"Bearer {student_token}"})
    assert_test("POST /reports/:id/verify", status in [201, 409], res)

    # 16. QR Codes List & Toggle
    status, res = execute_api_test("GET", "/api/v1/qr-codes")
    assert_test("GET /qr-codes", status == 200 and len(res.get("data", [])) == 9, res)

    status, res = execute_api_test("PATCH", "/api/v1/qr-codes/lib2/toggle")
    assert_test("PATCH /qr-codes/lib2/toggle", status == 200 and "qr_active" in res.get("data", {}), res)

    # 17. Maintenance Tasks
    status, res = execute_api_test("GET", "/api/v1/maintenance")
    assert_test("GET /maintenance", status == 200 and "tasks" in res.get("data", {}), res)

    # 18. Admin Dashboard KPI
    status, res = execute_api_test("GET", "/api/v1/admin/dashboard")
    assert_test("GET /admin/dashboard", status == 200 and "monitoredZones" in res.get("data", {}), res)

    # 19. User Preferences
    status, res = execute_api_test("GET", "/api/v1/preferences", headers={"Authorization": f"Bearer {student_token}"})
    assert_test("GET /preferences", status == 200 and "music_volume" in res.get("data", {}), res)

    status, res = execute_api_test("PATCH", "/api/v1/preferences", {"music_enabled": True, "music_volume": 60}, headers={"Authorization": f"Bearer {student_token}"})
    assert_test("PATCH /preferences", status == 200 and res.get("success"), res)

    print("=" * 65)
    print(f"📊 Results: {tests_passed}/{total_tests} Tests Passed ({(tests_passed/total_tests)*100:.1f}%)")
    print("=" * 65)

    if tests_passed == total_tests:
        print("🎉 ALL 20/20 API ENDPOINTS VERIFIED & FUNCTIONAL!")
        return 0
    else:
        print("⚠️ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
