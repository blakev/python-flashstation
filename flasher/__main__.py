import os
import sys
import json
import logging
from logging import getLogger
from logging.config import dictConfig

import click

from flasher.process import ensure_root, process_loop

logger = getLogger('flasher')


# yapf: disable
@click.command()
@click.option(
    '-c', '--clone',
    help='path to clone to the formatted usb',
    type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True),
    multiple=True)
@click.option(
    '--label',
    help='usb device label',
    type=str,
    default='FlashStation')
@click.option(
    '--tmp-mount',
    help='path for temporarily mounting usb drives',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    default=r'/tmp')
@click.option(
    '-n', '--concurrent',
    help='concurrent devices to operate on',
    default=1,
    type=click.IntRange(min=1))
def main(clone, label, tmp_mount, concurrent):
    # yapf: enable

    # setup logging
    log_config = os.path.join(os.getcwd(), 'logging.json')
    if os.path.isfile(log_config):
        with open(log_config, 'r') as fp:
            dictConfig(json.load(fp))
        getLogger('sh').setLevel(logging.ERROR)

    # ~~ setup
    click.echo('WARNING! THIS APPLICATION MUST BE RUN AS ROOT.')
    sudo = ensure_root()
    failure = False

    try:
        process_loop(clone, label, tmp_mount, concurrent, sudo)
    except KeyboardInterrupt:
        click.echo('shutting down')
    except Exception as e:
        failure = True
        logger.exception(e)
    sys.exit(failure)


main()
