# python-flashstation

USB stick flash/duplication station.

## About

Running as a background daemon python-flashstation scans for newly inserted mass storage.
All new devices are automatically purged and reformatted before cloning file and folder contents.
Copied files are validated by rsync-checksum as well as additional SHA1 checksum. Finalized devices
can be safely removed.


### Interface

```shell
[blake@desktop]$ python -m flasher --help
Usage: flasher [OPTIONS]

Options:
  -c, --clone PATH                Path to clone to the formatted USB.
                                  (multiple allowed)
  -x, --exclude TEXT              File extensions to exclude from cloning.
                                  (multiple allowed)
  --label TEXT                    USB device label.
  --tmp-mount DIRECTORY           Path for temporarily mounting USB drives.
  -n, --concurrent INTEGER RANGE  Concurrent devices to operate on.
  --help                          Show this message and exit.

```

### Running

```shell
[blake@desktop]$ sudo python -m flasher -x jpg -c /home/blake/Screenshots -n2

WARNING! THIS APPLICATION MUST BE RUN AS ROOT.

2018-10-21 15:56:32 INFO  flasher                     excluding from clone, {'.jpg'}
2018-10-21 15:56:32 INFO  flasher.callbacks           starting thread Thread-0
2018-10-21 15:56:32 INFO  flasher.callbacks           starting thread Thread-1
2018-10-21 15:56:32 DEBUG flasher.process             original device, (2316, 4096, 4, 18)
2018-10-21 15:56:32 INFO  flasher.process             ~ready
2018-10-21 15:56:46 INFO  flasher.process             found new device (2352, 25925, 2, 19) at /dev/sda
2018-10-21 15:56:46 INFO  flasher.callbacks           starting process on (2352, 25925, 2, 19) at /dev/sda
2018-10-21 15:56:46 INFO  flasher.callbacks./dev/sda  looking for device mount /dev/sda1 (1/5)
2018-10-21 15:56:47 INFO  flasher.callbacks./dev/sda  looking for device mount /dev/sda1 (2/5)
2018-10-21 15:56:48 INFO  flasher.callbacks./dev/sda  scrubbing partition table
2018-10-21 15:56:48 INFO  flasher.callbacks./dev/sda  creating partition table
2018-10-21 15:56:49 INFO  flasher.callbacks./dev/sda  looking for device mount /dev/sda1 (1/5)
2018-10-21 15:56:49 INFO  flasher.callbacks./dev/sda  looking for device mount /dev/sda1 (2/5)
2018-10-21 15:56:50 INFO  flasher.callbacks./dev/sda  looking for device mount /dev/sda1 (3/5)
2018-10-21 15:56:51 INFO  flasher.callbacks./dev/sda  looking for device mount /dev/sda1 (4/5)
2018-10-21 15:56:52 INFO  flasher.callbacks./dev/sda  looking for device mount /dev/sda1 (5/5)
2018-10-21 15:56:53 INFO  flasher.callbacks./dev/sda  creating new filesystem
2018-10-21 15:57:04 INFO  flasher.callbacks           scanning clone directories for hashsum
2018-10-21 15:57:04 INFO  flasher.callbacks           found 53 files
2018-10-21 15:57:04 INFO  flasher.callbacks./dev/sda  copying contents from directories
2018-10-21 15:57:12 INFO  flasher.callbacks./dev/sda  validation success? True
2018-10-21 15:57:12 INFO  flasher.callbacks./dev/sda  cleaning up
2018-10-21 15:57:13 INFO  flasher.callbacks./dev/sda  done
2018-10-21 15:57:13 INFO  flasher.callbacks           device copy success
^C
2018-10-21 15:57:17 INFO  flasher.callbacks           clearing thread fun flag
2018-10-21 15:57:17 INFO  flasher.callbacks           stoping thread Thread-0
2018-10-21 15:57:18 INFO  flasher.callbacks           stoping thread Thread-1
shutting down
```

### Attribution

Functionality provided by,

- [pyusb](https://github.com/pyusb/pyusb)
- [inotify](https://github.com/dsoprea/PyInotify)
- [sh](https://amoffat.github.io/sh/index.html)
- [click](https://click.palletsprojects.com/en/7.x/)
- [toolz](https://toolz.readthedocs.io/en/latest/index.html)