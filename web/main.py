"""Web interface for monitoring and configuring the Warmer."""
import subprocess
import csv
from collections import deque
from pathlib import Path
import threading
import time

from flask import (
    Flask,
    render_template_string,
    request,
    abort,
    send_file,
)

from web.environment import read_env, update_env
from web.config_html import CONFIG_PAGE
from web.restart_html import RESTART_PAGE
from web.logs_html import LOGS_PAGE
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


# Same directory used by log.py: project root / warmer.csv.
LOG_PATH = Path(__file__).resolve().parent.parent / "warmer.csv"
LOG_COLUMNS = ["Timestamp", "T0", "T1", "T2", "T3", "HTR"]


def available_logs():
    """Return the active log and rotated archives, newest first."""
    paths = [LOG_PATH, *LOG_PATH.parent.glob(LOG_PATH.name + ".*")]
    paths = [p for p in paths if p.is_file()]
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)


def selected_log(filename):
    """Only allow files discovered in the logger's directory."""
    for path in available_logs():
        if path.name == filename:
            return path
    abort(404)


@app.route('/logs')
def logs():
    """Show the most recent 200 readings without loading a whole log into RAM."""
    files = available_logs()
    names = [path.name for path in files]
    selected = request.args.get('file', names[0] if names else '')
    columns = LOG_COLUMNS
    rows = []

    if files:
        path = selected_log(selected)
        # Every data row has six columns; archive headers are optional.
        with path.open('r', encoding='utf-8', newline='') as stream:
            recent = deque((line for line in stream if line.strip()), maxlen=201)
        for line in reversed(recent):
            try:
                cells = next(csv.reader([line]))
            except csv.Error:
                continue
            if len(cells) == 6 and cells[0].strip().lower() != 'timestamp':
                rows.append(cells)
            if len(rows) == 200:
                break

    return render_template_string(
        LOGS_PAGE, files=names, selected=selected,
        columns=columns, rows=rows,
    )


@app.route('/logs/download/<filename>')
def download_log(filename):
    """Download a permitted log file without loading it into memory."""
    path = selected_log(filename)
    return send_file(path, as_attachment=True, download_name=path.name,
                     mimetype='text/csv')

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
