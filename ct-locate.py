#!/usr/bin/env python3

"""
.. module:: ct-locate.py
   :synopsis: Attempts to discover the physical location of a Chromecast
              device by rebooting it, requesting a list of the nearby
              Wi-Fi networks and sending their BSSIDs to the Google
              Geolocation API.

.. moduleauthor:: Rodrigo Laneth <rodrigo@rapidlight.io>
   :copyright: Copyright (c) 2018 Radialle (radialle.com)
   :license: MIT
"""

import sys
import json
import time
import urllib.request as request

from urllib.error import HTTPError, URLError

SLEEP_BETWEEN_SCAN = 4
REQUEST_TIMEOUT = 4

def usage():
    print(sys.argv[0], "[host]")
    exit(0)

# Place the Google APIs key for geolocation in a file named
# google-apis-key.txt in the same directory of the script.
def read_api_key():
    with open("google-apis-key.txt") as f:
        return f.readline()

# Requests Wi-Fi network scan results from the Chromecast device.
def get_scan_list():
    url = "http://{}:8008/setup/scan_results".format(host)
    return request.urlopen(url, timeout=REQUEST_TIMEOUT)

# Reboots the Chromecast device.
def post_reboot():
    url = "http://{}:8008/setup/reboot".format(host)
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"params": "now"}).encode("utf-8")
    r = request.Request(url, data, headers=headers)
    return request.urlopen(r, timeout=REQUEST_TIMEOUT)

# Attempts to retrieve a location from a list of access points by using the
# Google Geolocation API.
def geolocate(ap_list, api_key):
    url = "https://www.googleapis.com/geolocation/v1/geolocate?key={}" \
          .format(api_key)
    headers = {"Content-Type": "application/json"}
    data = json.dumps({ "wifiAccessPoints": ap_list }).encode("utf-8")
    r = request.Request(url, data, headers=headers)
    return request.urlopen(r, timeout=REQUEST_TIMEOUT)

def main():
    global host

    if (len(sys.argv) != 2):
        usage()

    host = sys.argv[1]
    api_key = read_api_key()

    print("Rebooting target ...")
    post_reboot()

    while True:
        time.sleep(SLEEP_BETWEEN_SCAN)
        print("Requesting Wi-Fi scan results ...")
        try:
            scan_list = json.loads( \
                get_scan_list().read().decode("utf-8") \
            )
        except (HTTPError, URLError) as e:
            # Errors are expected, since some requests might be sent while the
            # Chromecast is still rebooting.
            print(str(e))
            continue
        if (len(scan_list) > 1):
            # If the Wi-Fi scan results contain more than one network, we may
            # proceed to the next step.
            break
        print("Networks found: {}. Retrying.".format(len(scan_list)))

    # Create access point list for the Google Geolocation API.
    ap_list = []
    for result in scan_list:
        print()
        print("| {}".format(result["ssid"]))
        for ap in result["ap_list"]:
            print("| {} ({})".format(ap["bssid"], ap["signal_level"]))
            ap_object = { \
                "macAddress": ap["bssid"], \
                "signalStrength": ap["signal_level"] \
            }
            ap_list.append(ap_object)
    print()

    try:
        location = json.loads( \
            geolocate(ap_list, api_key).read().decode("utf-8") \
        )
    except HTTPError as e:
        # If we get an error from the Geolocation API, print it.
        print("The geolocation API replied: {}" \
              .format(e.read().decode("utf-8")))
        raise

    lat = location["location"]["lat"]
    lng = location["location"]["lng"]
    accuracy = location["accuracy"]

    print("Lat: {}".format(lat))
    print("Lng: {}".format(lng))
    print("Accuracy: {} meters".format(accuracy))
    print("Maps URL: https://www.google.com/maps/?q={},{}".format(lat, lng))
    print()

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        exit(0)
    except Exception as e:
        print("Error: {}".format(str(e)))
        exit(1)