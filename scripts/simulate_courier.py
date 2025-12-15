#!/usr/bin/env python3
"""
Simulator: set courier session and POST positions to the server so dashboard map shows movement.

Usage:
    python3 scripts/simulate_courier.py --courier 1 --steps 50 --interval 1

This script will:
 - call GET /courier_panel/dev/set_session/<courier_id>/ to get a session with courier_id
 - post position updates to /courier_panel/api/update_position/ every <interval> seconds

Adjust SERVER variable if your dev server runs elsewhere.
"""
import time
import math
import argparse
import requests

SERVER = 'http://127.0.0.1:8000'

DEFAULT_PATH_CENTER = (41.2995, 69.2401)  # default center (Tashkent example)


def generate_circle_path(center, radius_m=2000, steps=60):
    # approximate conversion: 1 deg lat ~ 111km, 1 deg lon ~ cos(lat)*111km
    lat0, lon0 = center
    deg_per_meter_lat = 1.0 / 111000.0
    deg_per_meter_lon = 1.0 / (111000.0 * math.cos(math.radians(lat0)))
    path = []
    for i in range(steps):
        theta = 2 * math.pi * (i / steps)
        dx = math.cos(theta) * radius_m
        dy = math.sin(theta) * radius_m
        lat = lat0 + dy * deg_per_meter_lat
        lon = lon0 + dx * deg_per_meter_lon
        path.append((lat, lon))
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--courier', type=int, required=True, help='Courier id to simulate (must exist)')
    p.add_argument('--steps', type=int, default=60, help='Number of position updates')
    p.add_argument('--interval', type=float, default=2.0, help='Seconds between updates')
    p.add_argument('--radius', type=int, default=2000, help='Radius in meters for circular path')
    p.add_argument('--server', default=SERVER, help='Server base URL')
    args = p.parse_args()

    sess = requests.Session()
    base = args.server.rstrip('/')

    # set session on server so API accepts courier_id
    set_url = f"{base}/courier_panel/dev/set_session/{args.courier}/"
    print('Setting session via:', set_url)
    r = sess.get(set_url)
    if r.status_code != 200:
        print('Failed to set session:', r.status_code, r.text)
        return
    print('Session set:', r.json())

    path = generate_circle_path(DEFAULT_PATH_CENTER, radius_m=args.radius, steps=args.steps)
    print(f'Starting simulation for courier {args.courier}: {len(path)} steps, interval {args.interval}s')

    update_url = f"{base}/courier_panel/api/update_position/"
    for idx, (lat, lon) in enumerate(path, start=1):
        payload = {'lat': lat, 'lon': lon, 'order_id': None}
        try:
            rr = sess.post(update_url, json=payload, timeout=5)
            print(f'[{idx}/{len(path)}] POST {lat:.6f},{lon:.6f} -> {rr.status_code} {rr.text}')
        except Exception as e:
            print('post error', e)
        time.sleep(args.interval)

    print('Simulation finished.')


if __name__ == '__main__':
    main()
