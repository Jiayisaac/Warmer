"""Web interface for monitoring and configuring the Warmer."""
import subprocess
import threading
import time

from flask import (
    Flask,
    render_template_string,
    request,
)

from web.environment import read_env, update_env
from web.config_html import CONFIG_PAGE
from web.restart_html import RESTART_PAGE
from wifi import WiFi

app = Flask(__name__)

def reboot_after_delay(delay=2):
    """Wait briefly before rebooting."""
    time.sleep(delay)
    subprocess.run(
        [
            'sudo',
            '/usr/sbin/reboot'
        ],
        check=False
    )

@app.route('/')
def configuration():
    """Display the Warmer configuration page."""
    values = read_env()

    try:
        networks = WiFi.networks()
    except Exception as error:
        print(
            f'Unable to scan Wi-Fi networks: {error}'
        )
        networks = []

    return render_template_string(
        CONFIG_PAGE,
        values=values,
        networks=networks,
    )

@app.route(
    '/save',
    methods=['POST']
)
def save():
    """Save Warmer configuration and restart."""
    current_values = read_env()
    new_values = {}

    for key in current_values:
        new_values[key] = request.form.get(
            key,
            ''
        )

    update_env(new_values)

    ssid = request.form.get(
        'wifi_ssid',
        ''
    ).strip()
    password = request.form.get(
        'wifi_password',
        ''
    )

    if ssid:
        try:
            WiFi.connect(
                ssid,
                password
            )
        except Exception as error:
            print(
                f'Unable to change Wi-Fi: {error}'
            )

    reboot_thread = threading.Thread(
        target=reboot_after_delay,
        daemon=True
    )
    reboot_thread.start()

    return RESTART_PAGE

def run_web_server():
    """Run the Flask web server using the active Flame instance."""
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )

if __name__ == '__main__':
    raise RuntimeError(
        'Run the web server through app.py so it receives the active Flame instance.'
    )