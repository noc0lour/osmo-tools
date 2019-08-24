#!/usr/bin/env python3

import subprocess
import argparse
import re
import datetime
import time
import os
from shutil import copy


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o',
        '--output_dir',
        help="Directory to save coredump infomartion",
        default='./coredumps/')
    return parser.parse_args()


def get_coredump_info(output_dir):
    info = subprocess.check_output(
        ['/usr/bin/coredumpctl', 'list', '--no-pager', '--no-legend'],
        shell=False).splitlines()
    # time, pid, uid, gid, sig  corefile, exe
    for line in info:
        data = line.split()
        # Extract dump info
        dump_time_format = ' '.join(list(d.decode('utf-8') for d in data[1:4]))
        dump_time = datetime.datetime(*(time.strptime(dump_time_format, '%Y-%m-%d %H:%M:%S %Z')[0:6]))
        dump_pid = data[4]
        dump_signal = data[7]
        dump_core_status = data[8]
        dump_cmd = data[9]
        if not dump_core_status == b'present' or not b'osmo' in dump_cmd:
            continue
        osmo_service_re = re.compile(b'.*osmo-(?P<service>\w*)$')
        service = osmo_service_re.match(dump_cmd)
        if service is None:
            continue
        service = service.group('service')
        result_dir = os.path.join(output_dir, "osmo-{}".format(service.decode('utf-8')),
                                  dump_time.isoformat())
        if os.path.exists(result_dir):
            continue
        # Get logs
        logs_start = dump_time - datetime.timedelta(minutes=5)
        logs_end = dump_time + datetime.timedelta(seconds=5)
        logs = subprocess.check_output([
            '/bin/journalctl',
            '-u', 'osmo-{}'.format(service.decode('utf-8')),
            '--since', '{}'.format(logs_start.strftime('%Y-%m-%d %H:%M:%S')),
            '--until', '{}'.format(logs_end.strftime('%Y-%m-%d %H:%M:%S')),
            '--no-pager',
        ])
        os.makedirs(result_dir, exist_ok=True)
        with open(os.path.join(result_dir, 'dump.log'), 'w') as dump_log:
            dump_log.write(logs.decode('utf-8'))
        # Get info & core path
        core = subprocess.check_output([
            '/usr/bin/coredumpctl', 'dump', '{}'.format(dump_pid.decode('utf-8')),
            '{}'.format(dump_cmd.decode('utf-8')),
            '--output','{}'.format(os.path.join(result_dir, 'core'))
        ])
        copy(dump_cmd.decode('utf-8'), result_dir)


def main():
    args = parse_args()
    get_coredump_info(args.output_dir)


if __name__ == "__main__":
    exit(not main())
