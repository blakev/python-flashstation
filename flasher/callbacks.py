import os
from queue import Queue, Empty as EmptyQueue
from logging import getLogger
from threading import Thread, Event

from sh import Command, ErrorReturnCode, cp, df, grep, rm

from flasher.util import pipe

logger = getLogger(__name__)

dd = Command('dd')
mkfs = Command('mkfs')
mount = Command('mount')
umount = Command('umount')
fdisk = Command('fdisk')
sync = Command('sync')
partprobe = Command('partprobe')
mkdir = Command('mkdir').bake('-p')
eject = Command('eject')
md5sum = Command('md5sum')


def get_md5sum(path):
    return md5sum(path).split()[0].strip()


class CallbackManager:
    def __init__(self, data):
        self._data = data
        self._queue = Queue()
        self._running = Event()
        self._running.set()
        self._last_modified = None
        self._hashsums = {}

        for n in range(data['concurrent']):
            name = 'Thread-%d' % n
            t = Thread(target=self._run, name=name)
            t.daemon = True
            t.start()
            logger.info('starting thread %s', name)

    def stop(self):
        logger.info('clearing thread fun flag')
        self._running.clear()

    def scan_clone_dirs(self):
        logger.info('scanning clone directories for hashsum')

        paths = self._data['clone']
        n = sum(map(lambda o: os.stat(o).st_mtime, paths))

        # check the modified times before re-validating the data
        if self._last_modified == n:
            return

        for path in paths:
            if os.path.isfile(path):
                self._hashsums[path] = get_md5sum(path)
                continue
            elif not os.path.isdir(path):
                logger.warning('skipping %s, not file or directory', path)
                continue
            for root, _, files in os.walk(path, followlinks=False):
                for file in files:
                    file = os.path.join(root, file)
                    self._hashsums[file] = get_md5sum(file)
        logger.info('found %d files', len(self._hashsums))

    def _run(self):
        while True:
            if not self._running.is_set():
                break
            try:
                info = self._queue.get(timeout=1.0)
            except EmptyQueue:
                continue
            device_id, device_path = info
            logger.info('starting process on %s(%s)', device_id, device_path)
            try:
                self._process(device_path)
            except ErrorReturnCode as e:
                logger.error(e)
            self._queue.task_done()
        logger.info('stopping thread')

    def _process(self, device):
        """Pipeline to format/prepare the usb device."""
        log = getLogger('%s.%s' % (__name__, device)).info
        partition = '%s1' % device
        tmp_mount = os.path.join(self._data['tmp_mount'], hex(abs(hash(device))))
        sudo = self._data['sudo']  # type: Command

        # ~~
        log('looking for device mount %s', partition)
        try:
            grep(df('-h'), partition)
        except ErrorReturnCode:
            pass
        else:
            sudo.unmount(partition)

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

        log('copying contents from directories')
        mkdir(tmp_mount)
        sudo.mount(partition, tmp_mount)
        for path in self._data['clone']:
            sudo.cp('-r', path, tmp_mount)
        sync()

        # ~~ TODO VALIDATION
        self.scan_clone_dirs()

        log('cleaning up')
        sudo.umount(partition)
        sudo.rm('-rf', tmp_mount)
        sudo.eject(device)
        log('done')

    def on_new_device(self, device_id, device_path):
        self._queue.put((
            device_id,
            device_path,
        ))

    def on_removed_device(self, device, mount):
        logger.info('device removed %s %s', device, mount)
