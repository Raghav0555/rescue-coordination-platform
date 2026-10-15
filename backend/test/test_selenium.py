"""
Selenium end-to-end (UI) tests for the field app and the control room dashboard.

The test starts everything it needs by itself:
  - the FastAPI backend (uvicorn) on a free port, with a fresh empty SQLite DB
  - a static file server for the frontend/ folder
  - a real Chrome browser driven by Selenium

Run from backend/ (venv active):
    python -m unittest test.test_selenium -v

Set HEADLESS=1 to hide the browser window, or DEMO_DELAY=1 to slow each step
down (in seconds) so it is easy to follow during a live demo.
"""
import functools
import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import json
import urllib.request

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait
except ImportError:  # pragma: no cover
    webdriver = None

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "frontend")
DEMO_DELAY = float(os.environ.get("DEMO_DELAY", "0"))
WAIT = 15


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class QuietServer(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass  # Chrome dropping keep-alive connections on exit is not an error


def pause():
    if DEMO_DELAY:
        time.sleep(DEMO_DELAY)


@unittest.skipIf(webdriver is None, "selenium is not installed (pip install selenium)")
class SeleniumUITests(unittest.TestCase):
    """Tests run in order (test_01, test_02, ...) and share one backend + browser."""

    @classmethod
    def setUpClass(cls):
        # 1. Backend on a free port, run inside a temp dir so it gets a fresh DB
        cls.db_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        api_port = free_port()
        env = dict(os.environ, PYTHONPATH=BACKEND_DIR)
        cls.backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(api_port)],
            cwd=cls.db_dir.name, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        cls.api = f"http://127.0.0.1:{api_port}/api"
        deadline = time.time() + 30
        while True:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{api_port}/health", timeout=1)
                break
            except Exception:
                if time.time() > deadline:
                    cls.backend.kill()
                    raise RuntimeError("Backend did not start")
                time.sleep(0.3)

        # 2. Static server for the frontend HTML files
        web_port = free_port()
        handler = functools.partial(QuietHandler, directory=FRONTEND_DIR)
        cls.web = QuietServer(("127.0.0.1", web_port), handler)
        threading.Thread(target=cls.web.serve_forever, daemon=True).start()
        cls.site = f"http://127.0.0.1:{web_port}"

        # 3. Chrome (Selenium Manager downloads the matching chromedriver)
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS") == "1":
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1400,900")
        cls.driver = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.driver, WAIT)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.web.shutdown()
        cls.backend.terminate()
        cls.backend.wait(timeout=10)
        cls.db_dir.cleanup()

    # ---------- helpers ----------

    def open_page(self, page, api=None):
        """Open a frontend page and point it at the test backend via the API URL box."""
        d = self.driver
        d.get(f"{self.site}/{page}")
        box = d.find_element(By.ID, "api-url-input")
        box.clear()
        box.send_keys(api or self.api)
        d.find_element(By.XPATH, "//button[text()='Save']").click()
        pause()

    def evidence_count(self):
        with urllib.request.urlopen(f"{self.api}/evidence/") as r:
            return len(json.load(r))

    def toast_text(self):
        # textContent, not .text: Selenium returns "" for a toast that has faded out
        return self.driver.find_element(By.ID, "toast").get_attribute("textContent")

    def submit_evidence(self, ev_type):
        d = self.driver
        before = self.evidence_count()
        d.find_element(By.CSS_SELECTOR, f".type-btn[data-type='{ev_type}']").click()
        pause()
        d.find_element(By.ID, "submit-btn").click()
        self.wait.until(lambda _: self.evidence_count() == before + 1)
        self.wait.until(lambda _: "Evidence submitted" in self.toast_text())
        pause()

    def open_dashboard(self):
        self.open_page("dashboard.html")
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "conn-status"), "live"))

    # ---------- tests ----------

    def test_01_submit_button_disabled_until_type_selected(self):
        self.open_page("field-app.html")
        btn = self.driver.find_element(By.ID, "submit-btn")
        self.assertFalse(btn.is_enabled())
        self.assertEqual(btn.text, "Select evidence type first")

        self.driver.find_element(By.CSS_SELECTOR, ".type-btn[data-type='Thermal']").click()
        pause()
        self.assertTrue(btn.is_enabled())
        self.assertEqual(btn.text, "Submit Thermal Evidence")

    def test_02_field_app_submits_thermal_evidence(self):
        self.open_page("field-app.html")
        self.submit_evidence("Thermal")
        self.assertIn("Evidence submitted and fused", self.toast_text())

    def test_03_dashboard_shows_zone_with_confidence(self):
        self.open_dashboard()
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "zones-list"), "30% confidence"))
        zones = self.driver.find_elements(By.CSS_SELECTOR, "#zones-list .card")
        self.assertEqual(len(zones), 1)
        self.assertIn("Unsearched", zones[0].text)
        pause()

    def test_04_more_evidence_raises_alert_on_dashboard(self):
        self.open_page("field-app.html")
        self.submit_evidence("Audio")
        self.submit_evidence("Visual")

        self.open_dashboard()
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "zones-list"), "75% confidence"))
        alert_card = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#alerts-list .card"))
        )
        self.assertIn("High", alert_card.text)
        self.assertIn("score 75", alert_card.text)
        pause()

    def test_05_create_team_from_dashboard(self):
        self.open_dashboard()
        self.driver.find_element(By.ID, "new-team-name").send_keys("Alpha Squad")
        pause()
        self.driver.find_element(By.XPATH, "//button[text()='Create Team']").click()
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "team-select"), "Alpha Squad"))
        pause()

    def test_06_assign_task_then_duplicate_is_blocked(self):
        d = self.driver
        self.open_dashboard()
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "team-select"), "Alpha Squad"))
        Select(d.find_element(By.ID, "team-select")).select_by_visible_text("Alpha Squad")
        assign = d.find_element(By.XPATH, "//button[text()='Assign Nearest Team']")

        assign.click()
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "zones-list"), "Assigned"))
        pause()

        # Second assignment for the same zone must be rejected (FR-4.4, HTTP 409)
        assign.click()
        popup = self.wait.until(EC.alert_is_present())
        self.assertIn("Could not assign", popup.text)
        self.assertIn("already has an active task", popup.text)
        pause()
        popup.accept()

    def test_07_acknowledge_alert_removes_it(self):
        self.open_dashboard()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#alerts-list .card")))
        self.driver.find_element(By.XPATH, "//button[text()='Acknowledge']").click()
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "alerts-list"), "No active alerts"))
        pause()

    def test_08_offline_submission_is_queued(self):
        # Point the field app at a port where nothing is listening
        self.open_page("field-app.html", api=f"http://127.0.0.1:{free_port()}/api")
        self.driver.find_element(By.CSS_SELECTOR, ".type-btn[data-type='GPS']").click()
        self.driver.find_element(By.ID, "submit-btn").click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "queue-note")))
        self.assertIn("1 item(s) pending sync", self.driver.find_element(By.ID, "queued-count").text)
        pause()


if __name__ == "__main__":
    unittest.main(verbosity=2)
