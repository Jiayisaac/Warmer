"""HTML template for the Warmer restart page."""
RESTART_PAGE = """
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Restarting Warmer</title>

    <style>

        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding-top: 100px;
            background: #f4f4f4;
        }

        .container {
            max-width: 500px;
            margin: auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
        }

        .back {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 20px;
            background: #cccccc;
            color: black;
            text-decoration: none;
            border-radius: 5px;
        }

    </style>

</head>

<body>

    <div class="container">

        <h1>Configuration saved</h1>

        <p>
            Warmer is restarting...
        </p>

        <p>
            Reconnect once the device has restarted.
        </p>

        <a
            class="back"
            href="/"
        >
            Back
        </a>

    </div>

</body>

</html>
"""