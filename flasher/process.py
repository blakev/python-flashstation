import os
import time
from getpass import getpass
from logging import getLogger
from collections import deque

import usb.core
import usb.util
from click import echo
from toolz.functoolz import curry
from inotify.adapters import Inotify
from sh import Command, ErrorReturnCode, sudo

from flasher.constants import MASS_STORAGE, STORAGE_DEV_RE
from flasher.callbacks import CallbackManager
from flasher.util import *

logger = getLogger(__name__)


def ensure_root():
    """Check that we can execute commands as sudo/root."""
    password = None
    try:
        sudo.sync()
    except ErrorReturnCode:
        logger.debug('not running as root')
        password = getpass('[sudo] password: ')
    if password:
        password = password.strip() + '\n'
        sudo.bake('-S', _in=password)
    try:
        sudo.sync()
    except Exception:
        echo('cannot execute as root, exiting')
        exit(1)
    return sudo


class FindClass(object):
    """Device helper for pyusb -- looks for device attributes on all layers."""

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
    """Scan the USB interfaces for all mass storage devices."""
    for dev in usb.core.find(find_all=True, custom_match=FindClass(MASS_STORAGE)):
        yield (dev.idVendor, dev.idProduct, dev.port_number, dev.address)


@curry
def process_state(notify, last_events, orig_devices, cur_devices):
    """Analyze the environment given Inotify events and currently tracked devices."""
    new_devices = {}
    for event in notify.event_gen(yield_nones=False, timeout_s=1.5):
        raw_event, types, path, file = event
        # skip devices that don't look like /dev/sda
        if not STORAGE_DEV_RE.match(file):
            continue
        for type_ in types:
            last_events.append(type_)
        breakout = False
        # IN_ACCESS spam seems to be indicative of adding a new usb storage device
        if all_eq('IN_ACCESS', last_events):
            for device in usb_storage_devices():
                # we don't care about the original devices
                if device in orig_devices:
                    continue
                # we also don't care about the current devices
                if device in cur_devices:
                    continue
                # dict[tuple, str]: device identifier mapped to device path.
                new_devices[device] = os.path.join(path, file)
                breakout = True
        if breakout:
            time.sleep(5.0)
            break
    return new_devices


def process_loop(clone, label, tmp_mount, concurrent, exclude, sudo):
    """Drop into the iNotify loop continually scanning for new devices.

    Args:
        clone: list of files/folders that need to be put on formatted drives.
        label: name to apply to the formatted drives.
        tmp_mount: mount folder for the formatted device to clone files to.
        concurrent (int): number of concurrent threads for writing.
        exclude (Set[str]): file extensions to ignore while cloning.
        sudo (Command): sudo/root password (if we need it)
    """
    # what we want to do with each device
    data = {
        'clone': clone,
        'label': label,
        'tmp_mount': tmp_mount,
        'concurrent': concurrent,
        'exclude': exclude,
        'sudo': sudo
    }

    manager = CallbackManager(data)
    notify = Inotify(paths=['/dev'])

    # map the device identifier of our "original usb sticks" so
    #  we don't accidentally  overwrite something that was already plugged in.
    # However, this will not count against original devices that are
    #  unplugged and plugged back in.
    original_devices = {o: None for o in usb_storage_devices()}
    current_devices = {}

    for device in original_devices.keys():
        logger.debug('original device, %s', device)

    # track the Inotify events in a loop.
    last_events = deque(list(), maxlen=6)

    # prime the state; curry
    get_state = process_state(notify, last_events, original_devices)

    logger.info('~ready')

    while True:
        new_devices = get_state(current_devices)

        if new_devices:
            # device was added
            for device, mount in new_devices.items():
                logger.info('found new device %s at %s', device, mount)
                current_devices[device] = mount
                manager.on_new_device(device, mount)
            continue

        current_usb = usb_storage_devices()

        for device in list(current_devices.keys()):
            if device not in current_usb:
                # device was removed
                mount = current_devices.pop(device)
                logger.info('device was removed %s from %s', device, mount)
                manager.on_removed_device(device, mount)
    # infinite loop
