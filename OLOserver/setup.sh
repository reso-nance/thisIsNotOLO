#!/bin/bash
# This script install dependancies and configure the network for the raspberry pi server
# usage : bash setup.sh

thisScriptDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
thisClientHostname="OLOserver"

echo "
------------installing dependencies :------------
"
echo "
updating the system :"
sudo apt-get update||exit 1
sudo apt-get -y dist-upgrade||exit 1
echo "
installing .deb packages :"
sudo apt-get -y --fix-missing install python3-pip python3-dev liblo-dev libasound2-dev libjack-jackd2-dev portaudio19-dev ||exit 1
echo "
installing pip packages :"
pip3 install Cython||exit 2
pip3 install pyliblo ||exit 2
pip3 install flask||exit 2
pip3 install flask-socketio||exit 2
pip3 install eventlet||exit 2

echo "
------------DONE installing dependencies------------
"

echo "
--------------- disabling bluetooth :---------------
"
echo "
dtoverlay=pi3-disable-bt
">>/boot/config.txt
systemctl disable hciuart.service
systemctl disable bluealsa.service
systemctl disable bluetooth.service

echo "
----------------configuring network :----------------
echo "  setting up the wifi country as FR..."
sudo raspi-config nonint do_wifi_country FR
echo "  setting hostname to $thisClientHostname..."
raspi-config nonint do_hostname "$thisClientHostname"
echo "  adding malinette network to wifi access points..."
echo '
network={
ssid="malinette"
psk="malinette666"
proto=RSN
key_mgmt=WPA-PSK
pairwise=CCMP
auth_alg=OPEN
}
'>>/etc/wpa_supplicant/wpa_supplicant.conf
echo "  configuring IP forwarding"
 if [ -f /etc/sysctl.conf ]; then cp /etc/sysctl.conf /etc/sysctl.conf.orig; fi
# uncomment net.ipv4.ip_forward=1
 sed -i -e 's/\#net.ipv4.ip_forward\=1/net.ipv4.ip_forward\=1/g'  /etc/sysctl.conf
 iptables -t nat -A  POSTROUTING -o eth0 -j MASQUERADE
# redirect port 8080 to port 80
 iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
# same for localhost/loopback (not needed for now)
 iptables -t nat -I OUTPUT -p tcp -d 127.0.0.1 --dport 80 -j REDIRECT --to-ports 8080
 if [ -f /etc/iptables.ipv4.nat ]; then cp /etc/iptables.ipv4.nat /etc/iptables.ipv4.nat.orig; fi
 sh -c "iptables-save > /etc/iptables.ipv4.nat"
 echo "/etc/iptables.ipv4.nat:"
 cat /etc/iptables.ipv4.nat

if [ -f /etc/rc.local ]; then cp /etc/rc.local /etc/rc.local.orig; fi
#add "iptables-restore < /etc/iptables.ipv4.nat \n iwconfig wlan0 power off" before "exit 0" in /etc/rc.local 
sed -i -e '/#/! s/exit\ 0/iptables\-restore\ \<\ \/etc\/iptables.ipv4.nat\
iw\ wlan0\ set\ power_save\ off\
exit\ 0/g' /etc/rc.local
echo "/etc/rc.local:"
cat /etc/rc.local

echo "adding redirections from bergen.olo to localhost"
echo "address=/bergen.olo/127.0.0.1
address=/www.bergen.olo/127.0.0.1
" >> /etc/dnsmasq.d/bergen.olo

echo "
--------------setting up script autolaunch:--------------
"
echo"
su pi -c 'cd /home/pi/OLOserver && python3 main.py&'
">>/etc/rc.local

echo "
----------------------------------------------------
-------------- DONE, leaving setup.sh---------------
--------- this pi will reboot in 5 seconds----------
----------------------------------------------------
"
sleep 5
reboot

