import os
import re
import sys
import json
import getpass
import logging
from tempfile import gettempdir
from collections import deque
from threading import Thread
from logging import getLogger
from logging.config import dictConfig

import sh
import usb.core
import usb.util
from toolz.functoolz import curry
from inotify.adapters import Inotify
from sh import Command, ErrorReturnCode, cp, df, grep, rm

logger = getLogger('flasher')
getLogger('sh').setLevel(logging.ERROR)
dictConfig(json.load(open('logging.json', 'r')))

# STATIC
LABEL = 'FlasherTest'
MASS_STORAGE = 0x8
STORAGE_DEV_RE = re.compile('sd\w$')
TMP_MOUNT = os.path.join(gettempdir(), 'usb')
SRC_DIR = '/home/blake/logs'
PASSWORD = os.getenv('ROOT_PASSWORD', None)

if PASSWORD is None:
    PASSWORD = getpass.getpass('sudo password: ')
PASSWORD = PASSWORD.strip() + '\n'


# COMMANDS
dd = Command('dd')
mkfs = Command('mkfs.ext4')
mount = Command('mount')
umount = Command('umount')
fdisk = Command('fdisk')
sync = Command('sync')
partprobe = Command('partprobe')
mkdir = Command('mkdir').bake('-p')
eject = Command('eject')
sudo = sh.sudo.bake('-S', _in=PASSWORD)


def pipe(ins):
    return [c + '\n' for c in ins]


def all_eq(val, seq):
    for obj in seq:
        if obj != val:
            return False
    return True


def dev_name(tup):
    return '_'.join(map(hex, map(int, tup)))


class find_class(object):
    # taken from the `pyusb` tutorial to recursively search a device for its type.

    def __init__(self, class_):
        self._class = class_

    def __call__(self, device):
        if device.bDeviceClass == self._class:
            return True
        for cfg in device:
            iface = usb.util.find_descriptor(cfg, bInterfaceClass=self._class)
            if iface is not None:
                return True
        return False


def usb_storage_devices():
    for dev in usb.core.find(find_all=True, custom_match=find_class(MASS_STORAGE)):
        yield (
            dev.idVendor,
            dev.idProduct,
            dev.port_number,
            dev.address,
        )


@curry
def process_state(notify, last_actions, orig_devices, cur_devices):
    new_devices = {}
    for event in notify.event_gen(yield_nones=False, timeout_s=2.5):
        raw_event, types, path, file = event
        if not STORAGE_DEV_RE.match(file):
            continue
        for type_ in types:
            last_actions.append(type_)
        breakout = False
        if all_eq('IN_ACCESS', last_actions):
            for device in usb_storage_devices():
                if device in orig_devices:
                    continue
                if device in cur_devices:
                    continue
                new_devices[device] = os.path.join(path, file)
                breakout = True
        if breakout:
            break
    return new_devices


def on_new_device(device, mount):
    def _run(device):
        log = getLogger('flasher.%s' % mount).info
        DEV = device
        PART = '%s1' % DEV
        tmp_mount = os.path.join(TMP_MOUNT, hex(abs(hash(device))))

        log('looking for device mount')
        try:
            grep(df('-h'), PART)
        except ErrorReturnCode:
            pass
        else:
            sudo.umount(PART)

        log('scrubbing partition table')
        sudo.dd('if=/dev/zero', 'of=' + DEV, 'bs=1M', 'count=25')
        sync()

        log('creating new partition table')
        flow = [
            PASSWORD,
            'g',  # GPT partition table
            'n',  # new partition
            '1',  # number "1"
            '',  # <first sector default>
            '',  # <last sector default>
            '',  # <>
            'w'  # <write>
        ]
        sudo.fdisk(DEV, _in=pipe(flow))
        sync()

        log('creating new file system')
        sudo.partprobe(DEV)
        sudo.mkfs('-L', LABEL, PART)

        log('copying contents from src directory %s', SRC_DIR)
        mkdir(tmp_mount)
        sudo.mount(PART, tmp_mount)
        sudo.cp('-r', SRC_DIR, tmp_mount)
        sync()

        log('cleaning up')
        sudo.umount(PART)
        sudo.rm('-rf', tmp_mount)
        sudo.eject(DEV)
        log('done')

    name = dev_name(device)
    logger.info('launching new thread %s for %s-%s', name, device, mount)
    t = Thread(target=_run, name=name, args=(mount, ))
    t.daemon = True
    t.start()


def on_removed_device(device, mount):
    logger.info('device removed, %s %s', dev_name(device), mount)


def main():
    notify = Inotify(paths=['/dev'])

    # get the initial usb storage devices,
    #  the usb library doesn't know their mount point, just existence
    orig_devices = {o: '' for o in usb_storage_devices()}
    cur_devices = {}

    # track the inotify events
    last_actions = deque([], maxlen=5)

    # prepare against the environment
    get_state = process_state(notify, last_actions, orig_devices)

    while True:
        new_devices = get_state(cur_devices)

        if new_devices:
            cur_devices.update(new_devices)
            for device, mount in new_devices.items():
                on_new_device(device, mount)
            continue

        current = usb_storage_devices()

        for device in list(cur_devices.keys()):
            if device not in current:
                # missing device
                mount = cur_devices.pop(device)
                on_removed_device(device, mount)


if __name__ == '__main__':
    failure = False
    try:
        logger.info('starting')
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        failure = True
        logger.exception(e)
    sys.exit(failure)
