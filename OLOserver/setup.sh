#!/bin/bash
# This script install dependancies and configure the network for the raspberry pi server
# usage : bash setup.sh
# captive portal : add address=/#/10.0.0.100 in router GUI -> services -> dnsmasq opt

thisScriptDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
thisClientHostname="OLOserver"

echo "
------------installing dependencies :------------
"
echo "
updating the system :"
apt-get update||exit 1
apt-get -y dist-upgrade||exit 1
echo "
installing .deb packages :"
apt-get -y --fix-missing install python3-pip python3-dev liblo-dev libasound2-dev libjack-jackd2-dev portaudio19-dev libatlas-base-dev dnsmasq ||exit 1
echo "
installing pip packages :"
pip3 install Cython||exit 2
pip3 install numpy||exit 2
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
"
# echo "  setting up the wifi country as FR..."
# raspi-config nonint do_wifi_country FR
echo "  setting hostname to $thisClientHostname..."
raspi-config nonint do_hostname "$thisClientHostname"
# echo "  adding bergen.olo network to wifi access points..."
# echo '
# network={
#    ssid="bergen.olo"
#    key_mgmt=NONE
# }
# '>>/etc/wpa_supplicant/wpa_supplicant.conf

echo "  configuring IP forwarding"
 if [ -f /etc/sysctl.conf ]; then cp /etc/sysctl.conf /etc/sysctl.conf.orig; fi
# uncomment net.ipv4.ip_forward=1
 sed -i -e 's/\#net.ipv4.ip_forward\=1/net.ipv4.ip_forward\=1/g'  /etc/sysctl.conf
 iptables -t nat -A  POSTROUTING -o eth0 -j MASQUERADE
# redirect port 8080 to port 80
 iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
# same for localhost/loopback (not needed for now)
 iptables -t nat -I OUTPUT -p tcp -d 127.0.0.1 --dport 80 -j REDIRECT --to-ports 8080
#  iptables -t nat -I OUTPUT -p tcp -d 10.0.0.0/24 --dport 80 -j REDIRECT --to-ports 8080
 if [ -f /etc/iptables.ipv4.nat ]; then cp /etc/iptables.ipv4.nat /etc/iptables.ipv4.nat.orig; fi
 sh -c "iptables-save > /etc/iptables.ipv4.nat"
 echo "/etc/iptables.ipv4.nat:"
 cat /etc/iptables.ipv4.nat

if [ -f /etc/rc.local ]; then cp /etc/rc.local /etc/rc.local.orig; fi
#add "iptables-restore < /etc/iptables.ipv4.nat \n iwconfig wlan0 power off" before "exit 0" in /etc/rc.local 
sed -i -e '/#/! s/exit\ 0/iptables\-restore\ \<\ \/etc\/iptables.ipv4.nat\
iw\ wlan0\ set\ power_save\ off\
exit\ 0/g' /etc/rc.local

echo "adding redirections from every URLs to localhost"
systemctl stop dnsmasq
echo "address=/#/127.0.0.1
" >> /etc/dnsmasq.d/bergen.olo
systemctl start dnsmasq

# echo "
# -----------------installing nodogsplash:-----------------
# "
# echo "installing libmicrohttpd from source"
# apt-get install perl autoconf m4 -y --fix-missing
# tar -xf libmicrohttpd-latest.tar.gz
# cd libmicrohttpd-0.9.70
# ./configure && make && make install
# cd ..
# echo "installing dependencies to compile nodogsplash"
# apt get-install git -y --fix-missing &&\
# git clone https://github.com/nodogsplash/nodogsplash.git &&\
# cd nodogsplash
# echo "compiling and installing nodogsplash"
# make && make install && rm -rf ../nodogsplash
# echo "done"

echo "
--------------setting up script autolaunch:--------------
"
# since Im paid by the slashes let's use sed to replace exit 0 with our command
sed -i -e '/#/! s/exit\ 0/su\ pi\ -c\ \"cd\ '$thisScriptDir'\ \&\&\ python3\ main.py\&\"\
exit\ 0/g' /etc/rc.local
echo "/etc/rc.local:"
cat /etc/rc.local

echo "
----------------------------------------------------
-------------- DONE, leaving setup.sh---------------
--------- this pi will reboot in 5 seconds----------
----------------------------------------------------
"
sleep 5
reboot
