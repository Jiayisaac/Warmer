"""HTML template for the Warmer temperature logs page."""
LOGS_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Warmer Logs</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }
        .container { max-width: 700px; margin: auto; background: white; padding: 30px;
                     border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.15); }
        h1 { margin-top: 0; }
        .field { margin-bottom: 20px; }
        label { display: block; font-weight: bold; margin-bottom: 6px; }
        select { width: 100%; padding: 10px; box-sizing: border-box; font-size: 16px;
                 border: 1px solid #cccccc; border-radius: 5px; }
        .buttons { display: flex; gap: 10px; margin-top: 20px; }
        .button { flex: 1; display: block; padding: 12px; font-size: 16px; border: none;
                  border-radius: 5px; text-align: center; text-decoration: none; box-sizing: border-box; }
        .save { background: #007bff; color: white; }
        .cancel { background: #cccccc; color: black; }
        .navigation { margin-top: 30px; text-align: center; }
        .navigation a { color: #007bff; text-decoration: none; }
        .note { color: #666666; font-size: 0.9em; }
        .table-wrap { overflow-x: auto; max-height: 480px; overflow-y: auto;
                      border: 1px solid #dddddd; border-radius: 5px; }
        table { border-collapse: collapse; width: 100%; font-size: 14px; white-space: nowrap; }
        th, td { padding: 9px 12px; text-align: right; border-bottom: 1px solid #eeeeee; }
        th:first-child, td:first-child { text-align: left; }
        th { background: #f4f4f4; position: sticky; top: 0; }
        tr:nth-child(even) { background: #fafafa; }
        @media (max-width: 500px) { .container { padding: 18px; } .buttons { flex-direction: column; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>Temperature Logs</h1>
        <p class="note">Recent readings from the selected CSV file (newest first).</p>
        {% if files %}
        <form method="GET" action="{{ url_for('logs') }}">
            <div class="field">
                <label for="file">Log file</label>
                <select id="file" name="file" onchange="this.form.submit()">
                    {% for filename in files %}
                    <option value="{{ filename }}" {% if filename == selected %}selected{% endif %}>
                        {{ filename }}
                    </option>
                    {% endfor %}
                </select>
            </div>
        </form>
        <div class="table-wrap">
            <table>
                <thead><tr>
                    {% for column in columns %}<th>{{ column }}</th>{% endfor %}
                </tr></thead>
                <tbody>
                    {% for row in rows %}
                    <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
                    {% else %}
                    <tr><td colspan="6">No readings available.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <div class="buttons">
            <a class="button save" href="{{ url_for('download_log', filename=selected) }}">Download CSV</a>
            <a class="button cancel" href="{{ url_for('logs', file=selected) }}">Refresh</a>
        </div>
        {% else %}
        <p>No log files found yet.</p>
        {% endif %}
        <div class="navigation"><a href="{{ url_for('configuration') }}">Back to Configuration</a></div>
    </div>
</body>
</html>
"""
