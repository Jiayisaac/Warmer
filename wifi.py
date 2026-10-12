"""WiFi management for the Warmer project."""

import subprocess
import time


class WiFi:
    """Manage WiFi connections and the Warmer setup hotspot."""

    INTERFACE = 'wlan0'
    HOTSPOT_NAME = 'Warmer-Setup'
    HOTSPOT_PASSWORD = 'warmer123'
    CHECK_INTERVAL_SECS = 10
    STARTUP_GRACE_SECS = 10

    @staticmethod
    def _run(*args, check=True):
        """Run an nmcli command and return the result."""
        return subprocess.run(
            ['nmcli', *args],
            capture_output=True,
            text=True,
            check=check
        )

    @classmethod
    def active_connection(cls):
        """Return the active connection name for wlan0, or None."""
        result = cls._run(
            '-t',
            '-f',
            'GENERAL.CONNECTION',
            'device',
            'show',
            cls.INTERFACE,
            check=False
        )

        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            if ':' not in line:
                continue

            _, connection = line.split(':', 1)
            connection = connection.strip()

            if connection and connection != '--':
                return connection

        return None

    @classmethod
    def connected(cls):
        """Return True if wlan0 is connected to a normal WiFi network."""
        connection = cls.active_connection()

        return (
            connection is not None
            and connection != cls.HOTSPOT_NAME
        )

    @classmethod
    def hotspot_active(cls):
        """Return True if the Pumpkin setup hotspot is active."""
        return cls.active_connection() == cls.HOTSPOT_NAME

    @classmethod
    def networks(cls):
        """
        Scan for available WiFi networks.

        Multiple mesh access points advertising the same SSID
        are returned as a single network.
        """
        cls._run(
            'device',
            'wifi',
            'rescan',
            'ifname',
            cls.INTERFACE,
            check=False
        )

        time.sleep(2)

        result = cls._run(
            '-t',
            '-f',
            'SSID',
            'device',
            'wifi',
            'list',
            'ifname',
            cls.INTERFACE
        )

        networks = set()

        for line in result.stdout.splitlines():
            ssid = line.strip()

            if ssid:
                networks.add(ssid)

        return sorted(networks)

    @classmethod
    def configure_connection(cls, connection):
        """
        Configure a saved WiFi connection for reliable operation.

        The connection:
        - automatically reconnects after boot;
        - is not locked to a particular BSSID / mesh node;
        - has WiFi power saving disabled.
        """
        cls._run(
            'connection',
            'modify',
            connection,
            'connection.autoconnect',
            'yes',
            '802-11-wireless.bssid',
            '',
            '802-11-wireless.powersave',
            '2'
        )

    @classmethod
    def connect(cls, ssid, password):
        """
        Connect to a WiFi network and configure it for automatic
        reconnection and mesh operation.
        """
        cls.stop_hotspot()

        result = cls._run(
            'device',
            'wifi',
            'connect',
            ssid,
            'password',
            password,
            'ifname',
            cls.INTERFACE
        )

        connection = cls.active_connection()

        if connection and connection != cls.HOTSPOT_NAME:
            cls.configure_connection(connection)

        return result

    @classmethod
    def configure_active_connection(cls):
        """Apply preferred settings to the active normal WiFi connection."""
        connection = cls.active_connection()

        if (
            connection is None
            or connection == cls.HOTSPOT_NAME
        ):
            return False

        cls.configure_connection(connection)
        return True

    @classmethod
    def start_hotspot(cls):
        """Start the setup hotspot if no normal WiFi connection exists."""
        if cls.connected() or cls.hotspot_active():
            return

        cls._run(
            'device',
            'wifi',
            'hotspot',
            'ifname',
            cls.INTERFACE,
            'con-name',
            cls.HOTSPOT_NAME,
            'ssid',
            cls.HOTSPOT_NAME,
            'password',
            cls.HOTSPOT_PASSWORD
        )

    @classmethod
    def stop_hotspot(cls):
        """Stop the setup hotspot if it is active."""
        cls._run(
            'connection',
            'down',
            cls.HOTSPOT_NAME,
            check=False
        )

    @classmethod
    def service(cls):
        """
        Maintain WiFi availability.

        On startup, allow NetworkManager time to reconnect to a saved
        network. If that fails, start the Pumpkin setup hotspot.
        """
        time.sleep(cls.STARTUP_GRACE_SECS)

        if cls.connected():
            try:
                cls.configure_active_connection()
            except subprocess.CalledProcessError as error:
                print(
                    'Unable to configure WiFi connection: '
                    f'{error.stderr.strip()}'
                )
        elif not cls.hotspot_active():
            try:
                cls.start_hotspot()
            except subprocess.CalledProcessError as error:
                print(
                    'Unable to start WiFi hotspot: '
                    f'{error.stderr.strip()}'
                )

        while True:
            time.sleep(cls.CHECK_INTERVAL_SECS)

            if cls.hotspot_active():
                continue

            if cls.connected():
                continue

            try:
                cls.start_hotspot()
            except subprocess.CalledProcessError as error:
                print(
                    'Unable to start WiFi hotspot: '
                    f'{error.stderr.strip()}'
                )