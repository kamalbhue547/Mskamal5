# Mskamal5

Software Developer | Building cool things for the web | Open Source Enthusiast

## Featured project: iOS Sweet Portability Lab

A Linux research toolkit for **read-only Android device identification**. It is
not an iOS installer and does not unlock, reboot, or flash a phone.

> Upstream's separate experimental root-image flash erases Android `userdata`.
> The toolkit below does not flash devices.

### Try it on Linux

For a first-time checkout, install Git and Python 3.10 or newer, then paste:

```sh
git clone https://github.com/kamalbhue547/Mskamal5.git &&
cd Mskamal5/ios-sweet-portability &&
python3 -m unittest discover -s tests -q &&
python3 -m devicecheck --help
```

These commands download the project, run its mocked tests, and show the CLI
help. They do not need a phone. For package installation, connecting a device,
more commands, and explanations, see the [step-by-step guide](ios-sweet-portability/README.md#quick-start-linux).
