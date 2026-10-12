"""HTML template for the Warmer configuration page."""
CONFIG_PAGE = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Warmer Configuration</title>

    <style>

        body {
            font-family: Arial, sans-serif;
            background: #f4f4f4;
            margin: 0;
            padding: 20px;
        }

        .container {
            max-width: 700px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow:
                0 2px 10px
                rgba(0, 0, 0, 0.15);
        }

        h1 {
            margin-top: 0;
        }

        h2 {
            margin-top: 30px;
        }

        .field {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-weight: bold;
            margin-bottom: 6px;
        }

        input,
        select {
            width: 100%;
            padding: 10px;
            box-sizing: border-box;
            font-size: 16px;
            border: 1px solid #cccccc;
            border-radius: 5px;
        }

        .buttons {
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }

        button {
            flex: 1;
            padding: 12px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }

        .save {
            background: #007bff;
            color: white;
        }

        .reset,
        .cancel {
            background: #cccccc;
            color: black;
        }

        .navigation {
            margin-top: 30px;
            text-align: center;
        }

        .navigation a {
            color: #007bff;
            text-decoration: none;
        }

        hr {
            border: 0;
            border-top: 1px solid #dddddd;
            margin: 30px 0;
        }

        .note {
            color: #666666;
            font-size: 0.9em;
            margin-top: -10px;
            margin-bottom: 20px;
        }

        .modal-backdrop {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.45);
            align-items: center;
            justify-content: center;
            padding: 20px;
            z-index: 1000;
        }

        .modal-backdrop.visible {
            display: flex;
        }

        .modal {
            width: 100%;
            max-width: 430px;
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-sizing: border-box;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }

        .modal h2 {
            margin-top: 0;
        }

        .modal .buttons {
            margin-top: 25px;
        }

    </style>

</head>

<body>

    <div class="container">

        <h1>Warmer Configuration</h1>

        <form
            id="configuration-form"
            method="POST"
            action="{{ url_for('save') }}"
        >

            <h2>Wi-Fi</h2>

            <div class="field">

                <label for="wifi_ssid">
                    Wi-Fi Network
                </label>

                <select
                    id="wifi_ssid"
                    name="wifi_ssid"
                    class="tracked-setting"
                >

                    <option value="">
                        Don't change Wi-Fi
                    </option>

                    {% for network in networks %}

                        <option value="{{ network }}">
                            {{ network }}
                        </option>

                    {% endfor %}

                </select>

            </div>

            <div class="field">

                <label for="wifi_password">
                    Wi-Fi Password
                </label>

                <input
                    type="password"
                    id="wifi_password"
                    name="wifi_password"
                    class="tracked-setting"
                    autocomplete="new-password"
                >

            </div>

            <div class="note">
                Leave the Wi-Fi network unchanged if you
                only want to modify warmer settings.
            </div>

            <hr>

            <h2>Environment Variables</h2>

            {% for key, value in values.items() %}

                <div class="field">

                    <label for="{{ key }}">
                        {{ key }}
                    </label>

                    <input
                        type="text"
                        id="{{ key }}"
                        name="{{ key }}"
                        class="tracked-setting"
                        value="{{ value }}"
                    >

                </div>

            {% endfor %}

            <div class="buttons">

                <button
                    id="reset-button"
                    class="reset"
                    type="button"
                >
                    Reset
                </button>

                <button
                    class="save"
                    type="submit"
                >
                    Save and Restart
                </button>

            </div>

        </form>

        <div class="navigation">
            <a class="guarded-link" href="{{ url_for('logs') }}">View Temperature Logs</a>
        </div>

    </div>

    <div
        id="unsaved-modal"
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby="unsaved-title"
    >

        <div class="modal">

            <h2 id="unsaved-title">
                Unsaved changes
            </h2>

            <p>
                Values have been updated but not saved.
            </p>

            <div class="buttons">

                <button
                    id="cancel-warning"
                    class="cancel"
                    type="button"
                >
                    Cancel
                </button>

                <button
                    id="save-warning"
                    class="save"
                    type="button"
                >
                    Save and Restart
                </button>

            </div>

        </div>

    </div>

    <script>
        const form = document.getElementById('configuration-form');
        const modal = document.getElementById('unsaved-modal');
        let dirty = false;
        let submitting = false;
        let pendingAction = null;

        function showUnsavedWarning(action) {
            pendingAction = action;
            modal.classList.add('visible');
        }

        function hideUnsavedWarning() {
            modal.classList.remove('visible');
            pendingAction = null;
        }

        document.querySelectorAll('.tracked-setting').forEach((element) => {
            element.addEventListener('input', () => { dirty = true; });
            element.addEventListener('change', () => { dirty = true; });
        });

        form.addEventListener('submit', () => {
            submitting = true;
            dirty = false;
        });

        document.getElementById('reset-button').addEventListener('click', () => {
            if (dirty) {
                showUnsavedWarning(() => window.location.reload());
            } else {
                window.location.reload();
            }
        });

        document.querySelectorAll('.guarded-link').forEach((link) => {
            link.addEventListener('click', (event) => {
                if (!dirty) return;
                event.preventDefault();
                showUnsavedWarning(() => { window.location.href = link.href; });
            });
        });

        document.getElementById('cancel-warning').addEventListener('click', hideUnsavedWarning);

        document.getElementById('save-warning').addEventListener('click', () => {
            hideUnsavedWarning();
            form.requestSubmit();
        });

        window.addEventListener('beforeunload', (event) => {
            if (!dirty || submitting) return;
            event.preventDefault();
            event.returnValue = '';
        });
    </script>

</body>

</html>
"""