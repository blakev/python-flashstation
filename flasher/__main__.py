import os
import sys
import json
import logging
from tempfile import gettempdir
from logging import getLogger
from logging.config import dictConfig

import click

from flasher.process import ensure_root, process_loop

logger = getLogger('flasher')


# yapf: disable
@click.command()
@click.option(
    '-c', '--clone',
    help='Path to clone to the formatted USB. (multiple allowed)',
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True),
    multiple=True)
@click.option(
    '-x', '--exclude',
    help='File extensions to exclude from cloning. (multiple allowed)',
    type=str,
    multiple=True)
@click.option(
    '--label',
    help='USB device label.',
    type=str,
    default='FlashStation')
@click.option(
    '--tmp-mount',
    help='Path for temporarily mounting USB drives.',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    default=gettempdir())
@click.option(
    '-n', '--concurrent',
    help='Concurrent devices to operate on.',
    default=1,
    type=click.IntRange(min=1))
def main(clone, exclude, label, tmp_mount, concurrent):
    # yapf: enable

    # setup logging
    log_config = os.path.join(os.getcwd(), 'logging.json')
    if os.path.isfile(log_config):
        with open(log_config, 'r') as fp:
            dictConfig(json.load(fp))
        getLogger('sh').setLevel(logging.ERROR)

    # ~~ setup
    click.secho('WARNING! THIS APPLICATION MUST BE RUN AS ROOT.', fg='green')
    sudo = ensure_root()
    failure = False

    # process the file extensions
    exclude_ext = set()
    for entry in exclude:
        entry = entry.replace(',', ' ')
        for ext in entry.split():
            exclude_ext.add('.' + ext.strip('.'))
    logger.info('excluding from clone, %s', exclude_ext)

    try:
        process_loop(clone, label, tmp_mount, concurrent, exclude_ext, sudo)
    except KeyboardInterrupt:
        msg = 'shutting down'
        logger.info(msg)
        click.echo(msg)
    except Exception as e:
        failure = True
        logger.exception(e)
    sys.exit(failure)


main()
