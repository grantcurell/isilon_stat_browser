#!/usr/bin/env python3

"""
Connects to PAPI to download list of current keys.
Outputs an HTML app that provides an interface to browse stat keys.
"""

import argparse
import getpass
import logging
import urllib3

from stat_key_browser.browser_builder import BrowserBuilder


def get_args():
    parser = argparse.ArgumentParser(
        description="Generate a browsable interface for OneFS statistics keys."
    )
    parser.add_argument('-c', '--cluster', type=str, required=True,
                        help='Cluster IP or hostname')
    parser.add_argument('-u', '--user', type=str,
                        help='Username to authenticate to PAPI (prompted if omitted)')
    parser.add_argument('-p', '--password', type=str,
                        help='Password to authenticate to PAPI (prompted if omitted)')
    parser.add_argument('-l', '--log', dest='logfile', type=str,
                        help='Log to a file instead of STDERR')
    parser.add_argument('-x', '--anon-ip', action='store_true',
                        help='Do not store cluster IP in output')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    return parser.parse_args()


def main():
    urllib3.disable_warnings()
    args = get_args()

    if args.debug:
        log_lvl = logging.DEBUG
        logging.getLogger("urllib3").setLevel(logging.INFO)
    else:
        log_lvl = logging.INFO
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.basicConfig(
        level=log_lvl,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        filename=args.logfile if args.logfile else None
    )

    username = args.user or input("Cluster username: ")
    password = args.password or getpass.getpass()

    store_ip = not args.anon_ip
    bb = BrowserBuilder(args.cluster, username, password, store_ip)
    bb.build_browser()


if __name__ == '__main__':
    main()
