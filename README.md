# HallonDisp
Module based framework for small display applications.

## The UI
The UI is built up by 'pages' that contains 'widgets'. A widget could contain anything as long as it derive from a Tk Frame.
The main UI display a page (with widgets) and 2 buttons for navigating between the pages.

Pages can contain any number of widgets as long as they fit the screen size. The framework is built to support small touch-screens why there is no scroll bars displayed if the page overflow the screen size.

![HallonDisp screenshot](/images/HallonWidget.png?raw=true)

*Arrows on left and right side swith the active 'page'. The displayed page contain 4 widgets. LocalTimeWidget, CurrentPowerWidget, TemperatureWidget and DoorWidget.*

# The backround workers
You often need some kind of backround worker that either listen to or fetch data from some device. For this you can use a HallonWorker that runs on its own thread. A HallonWorker can then publich updates to the UI whenever new data is available.

There are some built-in workers that handle a few different IoT devices. Most of them subscribe on mqtt messages, process the message and then publich a ui friendly message through a Rx subject. The connection between a widget and its requiered workers are defined in the configuration file `hallondisp.json`.

A HallonWorker can be shared between multiple HallonWidgets. This makes it possible to have multiple widges backed by the same data source 

### Example
#### PowerWidgets
- IoT

  A blink-detector that send a mqtt message whenever the power-meter blinks. The IoT publich all messages on the topic `power` as a json string containg the time since last blink and an IoT id.
  
  
  ```
  { 
    "id" : "10702547_3",
    "power_tick_period" : 908
  }
  ```
- PowerWorker
  The worker subscribe on the topic `power`. When a message is recieved it extracts the `power_tick_period` and calculates the current power. The power is the publiched on the Rx subject `whenPowerReported`.
- CurrentPowerWidget
  The widget require a worker of type `PowerWorker`. At construction, the widget subscribes on `whenPowerReported` and updates the power-label when a new current power is reported.


# Installing on a rasberry Pi with a HyperPixel 4' display
## Prepare SD-card
- Download and flash a rasbian lite to a SD-card.
- Add a wpa_supplicant.conf file to the boot partition
  ```
  ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
  update_config=1
  country=SE
  
  network={
    ssid="SSID"
    psk="Passwd"
  }
  ```
- Add an empty file named `ssh` to the boot partition
- Boot the Raspberry Pi
- Connect: `ssh pi@raspberrypi.local`
- Change hostname (edit `/etc/hostname`)
- Reboot
- connect: `ssh pi@somehostname.local`

## Upgrade
```
sudo apt update
sudo apt upgrade
```

## Install apt packages
```
sudo apt update
sudo apt install python3-numpy python3-tk python3-pip xinit git unclutter
```

## Install HyperPixel display
https://github.com/pimoroni/hyperpixel4
(`curl -sSL https://get.pimoroni.com/hyperpixel4 | bash`)

## Clone HallonDisp repo
```
cd
git clone https://github.com/MikaelBertze/HallonDisp.git
```
Install pip packages
```
cd HallonDisp
sudo pip3 install -r requirements.txt
```

## Startup script
Create a startup script `/home/pi/kiosk.sh` and set it as executable with `chmod 744 /home/pi/kiosk.sh`

```
#!/bin/bash
xset s noblank
xset s off
xset -dpms

unclutter -idle 0 -root &

cd /home/pi/HallonDisp
python3.7 hallondisp.py
```

Now it's time to test it!
```
sudo xinit /home/pi/kiosk.sh
```

## Service setup
Create a systemd config file named `/lib/systemd/system/hallondisp.service`:
```
[Unit]
Description=HallonDisp startup service

[Service]
ExecStart=xinit /home/pi/kiosk.sh

[Install]
WantedBy=multi-user.target
```
Reload systemctl: `sudo systemctl daemon-reload`
Start service: `sudo systemctl start hallondisp`
Enable service: `sudo systemctl enable hallondisp` (auto-start)

Reboot!


