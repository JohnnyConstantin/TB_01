#!/usr/bin/env python3
import sys
import argparse
sys.path.insert(0, './app')
from Listing import Listing

if __name__ == '__main__':

    # set parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait_time', type=float, help='Wait some before check new coins (seconds)', default=1800)
    parser.add_argument('--time_delta', type=int, help='Time delta to search and show new coins (days)', default=30)
    parser.add_argument('--debug', help='Output all messages', action="store_true", default=False) # 0=True, 1=False
    parser.add_argument('--loop', type=int, help='Loop (0 unlimited)', default=0)
    option = parser.parse_args()

    # get start
    run = Listing(option)
    run.run()
