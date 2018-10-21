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

2018-10-20 19:16:11 INFO  flasher                     excluding from clone, {'.jpg'}
2018-10-20 19:16:11 INFO  flasher.callbacks           starting thread Thread-0
2018-10-20 19:16:11 INFO  flasher.callbacks           starting thread Thread-1
2018-10-20 19:16:11 DEBUG flasher.process             original device, (5451, 64005, 2, 22)
2018-10-20 19:16:11 INFO  flasher.process             ready
2018-10-20 19:16:25 INFO  flasher.process             found new device (5451, 64005, 4, 23) at /dev/sdi
2018-10-20 19:16:25 INFO  flasher.callbacks           starting process on (5451, 64005, 4, 23) at /dev/sdi
2018-10-20 19:16:25 INFO  flasher.callbacks./dev/sdi  looking for device mount /dev/sdi1 (1/3)
2018-10-20 19:16:26 INFO  flasher.callbacks./dev/sdi  looking for device mount /dev/sdi1 (2/3)
2018-10-20 19:16:27 INFO  flasher.callbacks./dev/sdi  scrubbing partition table
2018-10-20 19:16:28 INFO  flasher.callbacks./dev/sdi  creating partition table
2018-10-20 19:16:28 INFO  flasher.callbacks./dev/sdi  looking for device mount /dev/sdi1 (1/3)
2018-10-20 19:16:29 INFO  flasher.callbacks./dev/sdi  looking for device mount /dev/sdi1 (2/3)
2018-10-20 19:16:30 INFO  flasher.callbacks./dev/sdi  looking for device mount /dev/sdi1 (3/3)
2018-10-20 19:16:32 INFO  flasher.callbacks./dev/sdi  creating new filesystem
2018-10-20 19:16:49 INFO  flasher.callbacks           scanning clone directories for hashsum
2018-10-20 19:16:49 INFO  flasher.callbacks           found 53 files
2018-10-20 19:16:49 INFO  flasher.callbacks./dev/sdi  copying contents from directories
2018-10-20 19:16:54 INFO  flasher.callbacks./dev/sdi  validation success? True
2018-10-20 19:16:54 INFO  flasher.callbacks./dev/sdi  cleaning up
2018-10-20 19:16:55 INFO  flasher.callbacks./dev/sdi  done
```

### Attribution

Functionality provided by,

- [pyusb](https://github.com/pyusb/pyusb)
- [inotify](https://github.com/dsoprea/PyInotify)
- [sh](https://amoffat.github.io/sh/index.html)
- [click](https://click.palletsprojects.com/en/7.x/)
- [toolz](https://toolz.readthedocs.io/en/latest/index.html)