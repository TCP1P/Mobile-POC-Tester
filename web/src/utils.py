import subprocess
import re
import sys
from time import sleep

SU_PATH = '/system/xbin/su-48916722dabda77a42e59b85751e81bf'

def run_process(process, args):
    result = subprocess.run([process] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    stdout = result.stdout.decode('utf-8')
    stderr = result.stderr.decode('utf-8')
    print(stdout, file=sys.stderr)
    print(stderr, file=sys.stderr)

    return stdout, stderr

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException

def run_adb(args):
    return run_process('adb', ['-H', 'device', '-P', '5037'] + args)

def grant_all_permission(package_name: str):
    out, _ = run_adb(['shell', 'dumpsys', 'package', package_name])
    match = re.search(r"requested permissions:\n(.*?)(?:\n\n|\Z)", out, re.DOTALL)

    if not match:
        return

    permissions = re.findall(r"\s+([\w.]+)", match.group(1))

    for permission in permissions:
        if permission.startswith("android.permission."):
            run_adb(['shell', 'pm', 'grant', package_name, permission])

def grant_permission(package_name: str, permission: str):
    run_adb(['shell', 'pm', 'grant', package_name, permission])

def stop_app(package_name: str):
    run_adb(['shell', 'am', 'force-stop', package_name])

def start_app(package_name: str):
    stop_app(package_name)

    run_adb(['shell', 'monkey', '-p', package_name, '1'])

    while True:
        out, _ = run_adb(['shell', 'dumpsys', 'window', 'windows'])
        if package_name in out:
            break

        sleep(1)

def touch_screen(x: int, y: int):
    run_adb(['shell', 'input', 'tap', str(x), str(y)])

def touch_and_hold_screen(x: int, y: int, duration: int):
    run_adb(['shell', 'input', 'swipe', str(x), str(y), str(x), str(y), str(duration)])

def swipe_screen(x1: int, y1: int, x2: int, y2: int):
    run_adb(['shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2)])
