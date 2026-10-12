# warmer
Controller for sourdough warming box

Flash the RPI Zero W with with Raspberry Pi OS Lite 32bit
Hostname: pumpkin
Username: pi
Password: ******
Wi-Fi: ******
Wi-Fi country: Australia
Locale/timezone: Australia/Brisbane
Enable SSH: Yes

Update and upgrade packages:
sudo apt update
sudo apt full-upgrade -y

Enable I2C communication:
sudo raspi-config
Interface Options -> I2C -> Enable

Install python, pip, git, i2c tools and smbus:
sudo apt install -y python3 python3-pip python3-venv git i2c-tools python3-smbus libopenjp2-7 libtiff6 libjpeg62-turbo libfreetype6-dev python3-gpiozero python3-dev swig liblgpio-dev -y

Configure WiFi settings:
WIFI_SSID='[YOUR WIFI]'
sudo nmcli connection modify "$WIFI_SSID" 802-11-wireless.bssid '' connection.autoconnect yes\
sudo nmcli connection modify "$WIFI_SSID" 802-11-wireless.powersave 2

Clone the repository:
cd ~
git clone https://github.com/Jiayisaac/Warmer.git
cd Warmer

Install and activate python venv:
python -m venv --system-site-packages venv
source venv/bin/activate

Install requirements
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Test app works:
python main.py

Add warmer.service to:
/etc/systemd/system/warmer.service

Start the service:
sudo systemctl daemon-reload
sudo systemctl enable warmer.service
sudo systemctl start warmer.service

Check the service is running:
sudo systemctl status warmer.service