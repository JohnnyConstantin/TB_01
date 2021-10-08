#!/usr/bin/env python3

from argparse import ArgumentParser
from app.listing import Listing


if __name__ == '__main__':

    parser = ArgumentParser()  # parse options
    parser.add_argument('--wait_time', type=float, help='Wait some before check new coins (seconds)', default=1)
    parser.add_argument('--time_delta', type=int, help='Time delta to search and show new coins (days)', default=30)
    parser.add_argument('--debug', help='Output all messages', action="store_true", default=False)
    parser.add_argument('--loop', type=int, help='Loop (0 unlimited)', default=1)
    option = parser.parse_args()

    run = Listing(option)
    run.run()  # start
