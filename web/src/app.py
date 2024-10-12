import traceback

from typing import List
from flask import Flask, render_template, request, jsonify, send_file, session
from threading import Thread
from time import sleep

import os
import uuid
import re
import signal

from type import Status, Client, Queue
from utils import run_process, run_adb, timeout_handler, stop_app

from pow import Challenge, check

import glob
from importlib import import_module

DEV = os.environ.get("DEV")

print("DEV:", DEV)

app = Flask(__name__)
app.secret_key = os.urandom(24)

queue: List[Queue] = []

clients: List[Client] = []
client_files = glob.glob("challenges/*/client.py")
for client_file in client_files:
    client: Client = import_module(client_file.replace("/", ".")[:-3])
    dirname = client_file.split("/")
    client.CHALLENGE_NAME = dirname[1]
    clients.append(client)

signal.signal(signal.SIGALRM, timeout_handler)

class QueueThread(Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            for q in queue:
                if q.status == Status.PENDING_QUEUE:
                    package_name = None
                    try:
                        q.status = Status.INITIALIZING

                        for c in clients:
                            stop_app(c.MAIN_PACKAGE_NAME)

                        # run_adb(['uninstall', q.client.MAIN_PACKAGE_NAME])
                        
                        out, err = run_adb(['shell', 'pm', 'list', 'packages', q.client.MAIN_PACKAGE_NAME])
                        if q.client.MAIN_PACKAGE_NAME not in out:
                            out, err = run_adb(['install', '-r', f'challenges/{q.client.CHALLENGE_NAME}/challenge.apk'])
                            if 'Success' not in out:
                                q.status = Status.ERROR
                                q.error = 'Failed to Install the Main APK!'
                                continue

                        q.status = Status.INSTALLING_PROOF_OF_CONCEPT

                        out, err = run_process('aapt', ['dump', 'badging', f'uploads/{q.id}.apk'])
                        if err:
                            q.status = Status.ERROR
                            q.error = err
                            continue

                        package_name = re.search(r"package: name='(.*?)'", out).group(1)
                        if not package_name:
                            q.status = Status.ERROR
                            q.error = 'Invalid APK!'
                            continue

                        if package_name == q.client.MAIN_PACKAGE_NAME:
                            q.status = Status.ERROR
                            q.error = 'Your poc can\'t use the same package name as the challenge\'s!'
                            continue

                        out, err = run_adb(['install', '-r', f'uploads/{q.id}.apk'])
                        if 'Success' not in out:
                            q.status = Status.ERROR
                            q.error = 'Failed to Install the Proof of Concept APK!'
                        else:
                            if q.client.callback:
                                q.client.callback(package_name, q)

                            q.status = Status.TAKING_SCREENSHOT

                            run_adb(['shell', 'screencap', '-p', f'/data/local/tmp/{q.id}.png'])
                            run_adb(['pull', f'/data/local/tmp/{q.id}.png', f'screenshots/{q.id}.png'])
                            run_adb(['shell', 'rm', '-f', f'/data/local/tmp/{q.id}.png'])

                            q.status = Status.COMPLETED
                    except Exception as e:
                        traceback.print_exc()

                        q.status = Status.ERROR
                        q.error = str(e)
                    finally:
                        if package_name:
                            run_adb(['uninstall', package_name])

            sleep(1)

@app.route('/')
def index():
    challenges = []
    for client in clients:
        challenges.append(client.CHALLENGE_NAME)

    return render_template('index.html', challenges=challenges)

@app.route('/upload', methods=['POST'])
def upload():
    if not DEV:
        try:
            solution = request.form.get('solution')
            challenge = Challenge.from_string(session.get('challenge'))

            if not check(challenge, solution):
                return jsonify({'status': 'error', 'message': 'Incorrect solution!'})

            session.clear()
        except:
            return jsonify({'status': 'error', 'message': 'Invalid solution!'})

    chall_name = request.form.get('chall_name')
    if not chall_name:
        return jsonify({'status': 'error', 'message': 'Please specify the challenge name!'})

    client: Client = None
    for c in clients:
        if c.CHALLENGE_NAME == chall_name:
            client = c
            break

    if not client:
        return jsonify({'status': 'error', 'message': 'Invalid challenge!'})

    q = Queue(
        status=Status.PENDING_QUEUE,
        id=str(uuid.uuid4()),
        client=client,
    )
    queue.append(q)

    file = request.files['file']
    file.save('uploads/' + q.id + '.apk')

    return jsonify({'status': 'success', 'id': q.id})

@app.route('/status', methods=['GET'])
def status():
    id = request.args.get('id')
    for q in queue:
        if q.id == id:
            return render_template('status.html', queue=q)

    return 'Queue not found!'

@app.route('/screenshots/<id>', methods=['GET'])
def screenshots(id):
    path = os.path.basename(id)
    if not path.endswith('.png'):
        path += '.png'

    if not os.path.exists('screenshots/' + path):
        return 'Screenshot not found!'

    return send_file('screenshots/' + path, mimetype='image/png')

@app.before_request
def before_request():
    out, _ = run_adb(['devices'])
    if not out or 'device' not in out:
        return 'Device is not connected yet, please come back in few minutes!'

    out, _ = run_adb(['shell', 'getprop', 'sys.boot_completed', '2>&1'])
    if '1' not in out:
        return 'Device is not fully booted! Please come back in few minutes!'

    if not session.get('challenge'):
        session['challenge'] = str(Challenge.generate(10000))

if __name__ == '__main__':
    queue_thread = QueueThread()
    queue_thread.start()

    print('Server is running on http://0.0.0.0:5000!')

    if not DEV:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000)
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
