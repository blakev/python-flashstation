import os
import sys
import time
from queue import Queue, Empty as EmptyQueue
from logging import getLogger
from threading import Thread, Event, Lock

from click import secho
from toolz.itertoolz import concat
from sh import Command, CommandNotFound, ErrorReturnCode, df, grep, rm

from flasher.util import pipe

logger = getLogger(__name__)

try:
    dd = Command('dd')
    mkfs = Command('mkfs')
    mount = Command('mount')
    umount = Command('umount')
    fdisk = Command('fdisk')
    sync = Command('sync')
    partprobe = Command('partprobe')
    mkdir = Command('mkdir').bake('-p')
    eject = Command('eject')
    sha1sum = Command('sha1sum')
    rsync = Command('rsync')
except CommandNotFound as e:
    msg = 'command line tool not found, %s' % str(e)
    secho(msg, fg='green')
    logger.error(msg)
    sys.exit(1)


def get_sha1sum(path):
    return sha1sum(path).split()[0].strip()


class CallbackManager:
    def __init__(self, data):
        self._data = data
        self._queue = Queue()
        self._running = Event()
        self._running.set()
        self._threads = []

        # temporary mount points to clean up
        self._tmp_mounts = []

        # checksum validation
        self._lock = Lock()
        self._last_modified = None
        self._hashsums = {}

        for n in range(data['concurrent']):
            name = 'Thread-%d' % n
            t = Thread(target=self._run, name=name)
            t.daemon = True
            t.start()
            logger.info('starting thread %s', name)
            self._threads.append(t)

    def stop(self):
        logger.info('clearing thread fun flag')
        self._running.clear()
        for path in self._tmp_mounts:
            if os.path.exists(path):
                logger.info('removing stale tmp mount point, %s', path)
                self._data['sudo'].rm('-rf', path)
        for t in self._threads:
            logger.info('stoping thread %s', t.name)
            t.join(timeout=5.0)

    def scan_clone_dirs(self):
        logger.info('scanning clone directories for hashsum')

        self._lock.acquire()

        paths = self._data['clone']
        n = sum(map(lambda o: os.stat(o).st_mtime, paths))

        # check the modified times before re-validating the data
        if self._last_modified == n:
            logger.info('no changes detected')
            paths = []

        if paths:
            self._hashsums = {}

        excluded = self._data['exclude']

        for path in paths:
            if os.path.isfile(path):
                if os.path.splitext(path)[-1].lower() not in excluded:
                    self._hashsums[path] = get_sha1sum(path)
                continue
            elif not os.path.isdir(path):
                logger.warning('skipping %s, not file or directory', path)
                continue
            for root, _, files in os.walk(path, followlinks=False):
                for file in files:
                    file = os.path.join(root, file)
                    if os.path.exists(file) and \
                            not os.path.islink(file) and \
                            os.path.splitext(file)[-1].lower() not in excluded:
                        self._hashsums[file] = get_sha1sum(file)
        logger.info('found %d files', len(self._hashsums))
        self._lock.release()

    def validate_hashes(self, tmp_mount) -> bool:
        if not os.path.exists(tmp_mount):
            logger.warning('path does not exist')
            return False

        excluded = self._data['exclude']
        inv_hashsums = {v: k for k, v in self._hashsums.items()}

        for root, _, files in os.walk(tmp_mount, followlinks=False):
            for file in files:
                path = os.path.join(root, file)
                if os.path.exists(path) and \
                        os.path.isfile(path) and \
                        not os.path.islink(path) and \
                        os.path.splitext(path)[-1].lower() not in excluded:
                    sha1hash = get_sha1sum(path)
                    if sha1hash not in inv_hashsums:
                        logger.error('invalid hashsum for file, %s', path)
                        return False
                    del inv_hashsums[sha1hash]
        if inv_hashsums:
            for sha1hash, file in inv_hashsums.items():
                logger.error('missing file %s (%s)', file, sha1hash)
            return False
        return True

    def _run(self):
        while True:
            if not self._running.is_set():
                break
            try:
                info = self._queue.get(timeout=1.0)
            except EmptyQueue:
                continue
            device_id, device_path = info
            logger.info('starting process on %s at %s', device_id, device_path)
            try:
                self._process(device_id, device_path)
            except ErrorReturnCode as e:
                logger.error(e)
            self._queue.task_done()

    def _process(self, device_id, device_path):
        """Pipeline to format/prepare the usb device."""
        device = device_path
        log = getLogger('%s.%s' % (__name__, device)).info
        partition = '%s1' % device
        tmp_mount = os.path.join(self._data['tmp_mount'], hex(abs(hash(device))))
        sudo = self._data['sudo']  # type: Command

        # possible cleanup later
        self._tmp_mounts.append(tmp_mount)

        # yapf: disable
        # ~~
        def do_umount(max_attempts=5):
            for attempt in range(max_attempts):
                log('looking for device mount %s (%d/%d)',
                    partition,
                    attempt + 1,
                    max_attempts)
                time.sleep(0.75)
                try:
                    grep(df('-h'), partition)
                except ErrorReturnCode:
                    pass
                else:
                    try:
                        sudo.umount(partition)
                    except ErrorReturnCode:
                        time.sleep(0.5)
                    else:
                        return

        do_umount()

        log('scrubbing partition table')
        sudo.dd('if=/dev/zero', 'of=' + device, 'bs=4k', 'count=1000')
        sync()

        log('creating partition table')
        flow = [
            'g',  # GPT partition table
            'n',  # new partition
            '1',  # number "1"
            '',  # <first sector default>
            '',  # <last sector default>
            '',  # <>
            'w'  # <write>
        ]
        sudo.fdisk(device, _in=pipe(flow))
        sync()

        do_umount()
        time.sleep(1.0)

        log('creating new filesystem')
        sudo.partprobe(device)

        sudo.mkfs(
            '--type=ext4',
            'discard',
            '-b',  # block size
            '4096',
            '-L',  # label
            self._data['label'],
            partition)

        self.scan_clone_dirs()

        log('copying contents from directories')
        mkdir(tmp_mount)
        sudo.mount(partition, tmp_mount)
        for path in self._data['clone']:
            sudo.rsync(
                '--verbose',
                '--archive',
                '--copy-links',
                '--keep-dirlinks',
                '--checksum',
                '--whole-file',
                '--no-perms',
                '--no-owner',
                '--no-group',
                '--omit-dir-times',
                *list(concat([
                    ('--exclude', '*%s' % ext) for ext in self._data['exclude']])),
                path,
                tmp_mount)
        sync()

        success = self.validate_hashes(tmp_mount)
        log('validation success? %s', success)
        if not success:
            self.on_unsuccessful_copy(device_id, device_path)

        # yapf: enable
        log('cleaning up')
        sudo.umount(partition)
        sudo.rm('-rf', tmp_mount)
        sudo.eject(device)
        log('done')

        if success:
            self.on_successful_copy(device_id, device_path)

    def on_new_device(self, device_id, device_path):
        self._queue.put((
            device_id,
            device_path,
        ))

    def on_removed_device(self, device, mount):
        logger.info('device removed %s %s', device, mount)

    def on_successful_copy(self, device, mount):
        logger.info('device copy success')

    def on_unsuccessful_copy(self, device, mount):
        logger.info('device copy failed')
