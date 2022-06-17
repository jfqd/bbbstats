#!/usr/bin/python3

import requests
from hashlib import sha1
import xml.etree.ElementTree as xml
from collections import namedtuple
import json
import sys
import os


class BBBStats():
    Stats = namedtuple("Stats", ["total_rooms", "regular_rooms", "breakout_rooms", "total_users", "unique_users"])
    Urls = namedtuple("Urls", ["url", "request"])

    def __init__(self, url, secret):
        self.url = "{}/".format(url.strip("/"))
        self.secret = secret

    def make_url(self, path):
        url = "{}{}".format(self.url, path)
        request = path
        return self.Urls(url, request)

    def get_checksum(self, request):
        return sha1("{}{}".format(request, self.secret).encode("utf-8")).hexdigest()

    @property
    def get_stats(self):
        url = self.make_url("getMeetings")
        checksum = self.get_checksum(url.request)
        params = {"checksum": checksum}
        result = requests.get(url.url, params=params)
        xmldata = xml.fromstring(result.content)
        total_users = 0
        unique_users = 0
        regular_rooms = 0
        breakout_rooms = 0
        if not xmldata[0].text == "SUCCESS":
            raise ConnectionError("Unable to fetch data from server")
        if xmldata[1].text == "noMeetings":
            return self.Stats(0, 0, 0, 0, 0)
        for meeting in xmldata[1]:
            total_users += int(meeting[16].text)
            if meeting[24].text == "false":
                unique_users += int(meeting[16].text)
                regular_rooms += 1
            else:
                breakout_rooms += 1
        total_rooms = len(xmldata[1])
        return self.Stats(total_rooms, regular_rooms, breakout_rooms, total_users, unique_users)

    @property
    def get_stats_json(self):
        try:
            stats = self.get_stats
        except ConnectionError as err:
            raise err
        stats_dict = {
            "total_rooms": stats.total_rooms,
            "regular_rooms": stats.regular_rooms,
            "breakout_rooms": stats.breakout_rooms,
            "total_users": stats.total_users,
            "unique_users": stats.unique_users,
        }
        return json.dumps(stats_dict)


if __name__ == "__main__":
    config_path_list = [
        "/etc/bbbstats/config.json",
        os.path.expanduser("~/.config/bbbstats/config.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),
    ]
    for config_file in config_path_list:
        if os.path.isfile(config_file):
            break
    try:
        with open(config_file, "r") as fh:
            conf = json.load(fh)
    except FileNotFoundError:
        print("config.json not found")
        sys.exit(1)

    bbb = BBBStats(conf["ApiUrl"], conf["ApiSecret"])
    try:
        if "--json" in sys.argv:
            print(bbb.get_stats_json)
            sys.exit(0)
        stats = bbb.get_stats
    except ConnectionError as err:
        print(err)
        sys.exit(1)
    print("There are {} users ({} unique) online in {} meetings in {} regular rooms and {} breakout rooms.".format(stats.total_users, stats.unique_users, stats.total_rooms, stats.regular_rooms, stats.breakout_rooms))
