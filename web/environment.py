"""Environment variable management for the Warmer project."""
from pathlib import Path

ENV_FILE = Path(__file__).parent.parent / '.env'


def _strip_matching_quotes(value: str) -> str:
    """Remove one matching pair of surrounding quotes from a value."""
    value = value.strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('\"', "'"):
        return value[1:-1]

    return value


def read_env():
    """Read KEY=value entries from the .env file for display/editing."""
    values = {}

    if not ENV_FILE.exists():
        return values

    with ENV_FILE.open(
        'r',
        encoding='utf-8'
    ) as file:
        for line in file:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith('#'):
                continue

            if '=' not in stripped:
                continue

            key, value = stripped.split(
                '=',
                1
            )

            values[key.strip()] = _strip_matching_quotes(value)

    return values


def update_env(new_values):
    """
    Update existing KEY=value entries while preserving comments, blank lines
    and ordering. All environment values are written as quoted strings.
    """
    if not ENV_FILE.exists():
        raise FileNotFoundError(
            f'{ENV_FILE} does not exist.'
        )

    lines = ENV_FILE.read_text(
        encoding='utf-8'
    ).splitlines()

    output = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            output.append(line)
            continue

        if stripped.startswith('#'):
            output.append(line)
            continue

        if '=' not in line:
            output.append(line)
            continue

        key, old_value = line.split(
            '=',
            1
        )

        key = key.strip()
        old_value = old_value.strip()

        if key in new_values:
            value = str(new_values[key])

            # Preserve the existing quote character. All current environment
            # values are quoted; double quotes are the fallback for safety.
            quote = '"'
            if (
                len(old_value) >= 2
                and old_value[0] == old_value[-1]
                and old_value[0] in ('"', "'")
            ):
                quote = old_value[0]

            # The form contains the display value without surrounding quotes.
            # Re-add them here; type conversion happens when ENVIRONMENT is
            # imported, not in this web editor.
            value = value.replace('\\', '\\\\')
            value = value.replace(quote, f'\\{quote}')

            output.append(
                f'{key}={quote}{value}{quote}'
            )
        else:
            output.append(line)

    ENV_FILE.write_text(
        '\n'.join(output) + '\n',
        encoding='utf-8'
    )