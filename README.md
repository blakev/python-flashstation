# python-flashstation
USB stick flash/duplication station


```bash
[blake@desktop]$ python -m flasher --help
Usage: flasher [OPTIONS]

Options:
  -c, --clone PATH                path to clone to the formatted usb
  --label TEXT                    usb device label
  --tmp-mount DIRECTORY           path for temporarily mounting usb drives
  -n, --concurrent INTEGER RANGE  concurrent devices to operate on
  --help                          Show this message and exit.

```

Running:

```bash
[blake@desktop]$ sudo python -m flasher -c /home/blake/Code/github/python-flashstation -n 2
WARNING! THIS APPLICATION MUST BE RUN AS ROOT.
2018-10-19 15:40:44 INFO     flasher.callbacks           starting thread Thread-0
2018-10-19 15:40:44 INFO     flasher.callbacks           starting thread Thread-1
2018-10-19 15:40:44 DEBUG    flasher.process             original device, (2352, 25925, 2, 16)
2018-10-19 15:40:44 DEBUG    flasher.process             original device, (5451, 64005, 4, 9)
2018-10-19 15:41:26 INFO     flasher.process             found new device (2352, 25925, 4, 17) at /dev/sda
2018-10-19 15:41:26 INFO     flasher.callbacks           starting process on (2352, 25925, 4, 17)(/dev/sda)
2018-10-19 15:41:26 INFO     flasher.callbacks./dev/sda  looking for device mount /dev/sda1
2018-10-19 15:41:26 INFO     flasher.callbacks./dev/sda  scrubbing partition table
2018-10-19 15:41:26 INFO     flasher.callbacks./dev/sda  creating partition table
2018-10-19 15:41:27 INFO     flasher.callbacks./dev/sda  creating new filesystem
2018-10-19 15:41:37 INFO     flasher.callbacks./dev/sda  copying contents from directories
2018-10-19 15:41:42 INFO     flasher.callbacks           scanning clone directories for hashsum
2018-10-19 15:41:42 INFO     flasher.callbacks           found 79 files
2018-10-19 15:41:42 INFO     flasher.callbacks./dev/sda  cleaning up
2018-10-19 15:41:43 INFO     flasher.callbacks./dev/sda  done
```

