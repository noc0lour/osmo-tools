#!/usr/bin/env python3

import logging
import re
import argparse
import time

from prometheus_client import start_wsgi_server
from prometheus_client import Gauge

import asyncssh, asyncio
from telnetlib import Telnet
from threading import Thread

LOGGER = logging.getLogger("prometheus-femto-exporter")

DCH = Gauge("femto_DCH", "UEs in DCH", ("id", ))
FACH = Gauge("femto_FCH", "UEs in FCH", ("id", ))
PCH = Gauge("femto_PCH", "UEs in PCH", ("id", ))
CONTEXTS = Gauge("femto_context", "how many context are allocated", ("id", ))

GAUGECELLS = {"Fach": FACH, "Pch": PCH, "Dch": DCH}

HNBGW_CTRL_PORT =  4262



def find_hnbs(hnbgw, interval=30):
    telnet = Telnet(hnbgw, '4261')
    time.sleep(1)
    telnet.read_very_eager()
    telnet.write(b'show hnb all\n')
    HNB = re.compile(r'^HNB \(r=(?P<ip>.*):\d*\<-\>.*')
    hnbs = {}
    time.sleep(1)
    data = telnet.read_very_eager().decode('utf-8')
    data = data.replace('\r', '')
    lines = data.splitlines()
    for line in lines:
        result = HNB.match(line)
        if result is None:
            continue
        ipaddr = result.group('ip')
        hnb_id = ipaddr.split('.')[-1]
        hnbs[hnb_id] = ipaddr
    return hnbs


def scrape_hnb(hnb_id, ipaddr):
    telnet = Telnet(ipaddr, 8090)
    print('Huh')
    time.sleep(0.1)
    telnet.read_very_eager()
    telnet.write(
        b'get numActiveUes numUesInCellFach numUesInCellPch numUesInCellDch')
    time.sleep(0.1)
    data = telnet.read_very_eager().decode('utf-8')
    data = data.replace('\r', '')
    lines = data.splitlines()
    cells = re.compile(r'numUesInCell([a-zA-Z]*ch) \(.*\) = ([0-9]+)')
    contexts = re.compile(r'numActiveUes \(.*\) = ([0-9]+)')
    for line in lines:
        if cells.match(line):
            channel, value = cells.match(line).groups()
            if channel in GAUGECELLS:
                GAUGECELLS[channel].labels({"id": hnb_id}).set(int(value))
                LOGGER.info("read %s = %s", channel, value)
            elif contexts.match(line):
                value, = contexts.match(line).groups()
                CONTEXTS.labels({"id": hnb_id}).set(int(value))
                LOGGER.info("read %s = %s", "contexts", value)


def run_scraping(hnbgw):
    while True:
        hnbs = find_hnbs(hnbgw)
        for _ in range(6):
            for hnb_id, hnb_ip in hnbs.items():
                print(hnb_id, hnb_ip)
                scrape_hnb(hnb_id, hnb_ip)
            time.sleep(10)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hnbgw', default='localhost', help="hnbgw host")
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    start_wsgi_server(8888)
    run_scraping(args.hnbgw)


if __name__ == "__main__":
    exit(not main())
