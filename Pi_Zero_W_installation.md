# Driving Hexa from a Pi Zero W

## Installing the OS

You will first need to install the Raspian Lite OS. This is sometimes
refered to as a "Legacy" OS, as the original Zero can't support
64-bit Raspian. This is best done by installing the OS on a microSD
card using the "rpi-imager" utility.

**Important note:** You will need to edit the configuration options
using the rpi-imager tool before you begin to install the OS. In
particular you will need to:
* Configure the wifi
* Set up the basic user account
* Turn on SSH for password login

If you skip any of these steps, you will have a sad and have to
reimage.

Please use the rpi-imager tool if possible, since the "conventional"
ways of setting these options on a freshly-flashed microSD card
sometimes change.

## Installing the Pi

There are two plugs hanging from Hexa; one is power, one is
USB. The one attached to a red plug is the USB one. The power plug
goes into the USB connector closer to the end of the board. Plug in
power first, then the USB for the panels.

## Configuring the Pi

Assuming you set up the Pi with a username "user" and hostname
"hexascroller":

```
ssh user@hexascroller.lan
```

Now you'll need to install a few tools and utilites.

```
sudo apt install git pip vim libopenjp2-7
git clone https://github.com/nycresistor/Hexascroller.git
sudo pip install -r Hexascroller/hexaservice/requirements.txt
```

At this point you will want to edit the file
`Hexascroller/hexaservice/hexascroller.service` and make sure the
`WorkingDirectory` parameter is set correctly for the username you've
chosen; in our example,
```
WorkingDirectory=/home/user/Hexascroller/hexaservice
```

Then it's time to copy over and enable the service.

```
sudo cp Hexascroller/hexaservice/hexascroller.service /etc/systemd/system
systemctl start hexascroller.service
sudo systemctl enable hexascroller.service
```

And that should do it.
