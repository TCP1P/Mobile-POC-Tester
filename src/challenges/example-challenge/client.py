import random
from lamda.client import Device, Point, ApplicationOpStub, GrantType
from time import sleep
from type import Status, Queue

MAIN_PACKAGE_NAME = "com.aimar.id.example"
PROCESS_TIMEOUT = 5*60 # 5 minutes
CHALLENGE_NAME = "Example Challenge"


def run_exploit(device: Device, pocPackageName: str):
    exploit: ApplicationOpStub = device.application(pocPackageName)
    permissions = exploit.permissions()
    for permission in permissions:
        if permission.startswith("android.permission"):
            exploit.grant(permission, mode=GrantType.GRANT_ALLOW)
        exploit.start()

    while not exploit.is_foreground():
        pass


def run_application(device: Device):
    app: ApplicationOpStub = device.application(MAIN_PACKAGE_NAME)
    procs = device.enumerate_running_processes()
    for proc in procs:
        if proc.processName == MAIN_PACKAGE_NAME:
            app.stop()
            break

    app.start()
    while not app.is_foreground():
        pass


def callback(device: Device, pocPackageName: str, q: Queue):
    q.status = Status.RUNNING_PROOF_OF_CONCEPT

    run_exploit(device, pocPackageName)

    sleep(2.5)

    # just uncomment this line if you want to run the vulnerable application
    # q.status = Status.RUNNING_VULNERABLE_APPLICATION
    # run_application(device)

    sleep(2.5)

    # idk just randomly clicking to demonstrate the lambda client library
    # you can read more about it here: https://github.com/rev1si0n/lamda/wiki
    for _ in range(10):
        top, left, bottom, right = [0, 0, 1920, 1080]
        x = random.randint(left, right)
        y = random.randint(top, bottom)
        device.click(Point(x=x, y=y))
