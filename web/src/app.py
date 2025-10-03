import os
import uuid
import re
import time
import glob
from threading import Thread, Lock
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from importlib import import_module

from type import Status, Queue
from utils import run_process
from config import Config
from pow import Challenge, check

from lamda.client import *
from lamda.const import *
from device_manager import DeviceManager

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_FILE_SIZE

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)

# Initialize device manager
device_manager = DeviceManager("localhost")

queue = []
queue_lock = Lock()
clients = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def emit_queue_stats():
    with queue_lock:
        pending = len([q for q in queue if q.status == Status.PENDING_QUEUE])
        processing = len([q for q in queue if q.status not in [Status.COMPLETED, Status.ERROR, Status.PENDING_QUEUE]])
        queue_size = pending + processing
        
    socketio.emit('queue_stats', {'queue_size': queue_size})

def emit_status_update(queue_item, update_stats=True):
    status_data = {
        'id': queue_item.id,
        'status': queue_item.status.value if hasattr(queue_item.status, 'value') else queue_item.status,
        'error': queue_item.error,
        'created_at': queue_item.created_at.isoformat() if queue_item.created_at else None,
        'completed_at': queue_item.completed_at.isoformat() if queue_item.completed_at else None,
        'duration': queue_item.duration,
        'challenge': queue_item.client.CHALLENGE_NAME
    }
    socketio.emit('status_update', status_data, room=f'queue_{queue_item.id}')
    if update_stats:
        emit_queue_stats()

@app.route('/')
def index():
    challenges = [client.CHALLENGE_NAME for client in clients]
    
    if not device_manager.is_device_ready():
        return jsonify({'status': 'error', 'message': 'Device is not ready! Please come back later.'})
    
    if 'challenge' not in session:
        challenge = Challenge.generate(Config.POW_DIFFICULTY)
        session['challenge'] = str(challenge)
    
    return render_template('index.html', challenges=challenges)

@app.route('/upload', methods=['POST'])
def upload():
    if not device_manager.is_device_ready():
        return jsonify({'status': 'error', 'message': 'Device is not ready! Please come back later.'})

    if Config.ENABLE_POW:
        try:
            solution = request.form.get('solution')
            challenge = Challenge.from_string(session.get('challenge'))

            if not solution or not check(challenge, solution):
                return jsonify({'status': 'error', 'message': 'Incorrect solution!'})

            session.pop('challenge', None)
        except Exception:
            return jsonify({'status': 'error', 'message': 'Invalid solution or something went wrong!'})

    chall_name = request.form.get('chall_name')
    if not chall_name:
        return jsonify({'status': 'error', 'message': 'Please specify the challenge name!'})

    client = next((c for c in clients if c.CHALLENGE_NAME == chall_name), None)
    if not client:
        return jsonify({'status': 'error', 'message': 'Invalid challenge!'})

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded!'})
    
    file = request.files['file']
    if not file or file.filename == '' or not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file!'})

    with queue_lock:
        if len(queue) >= Config.MAX_QUEUE_SIZE:
            return jsonify({'status': 'error', 'message': 'Queue is full, please try again later!'})

    queue_id = str(uuid.uuid4())
    filename = secure_filename(f"{queue_id}.apk")
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    file.save(file_path)

    with queue_lock:
        q = Queue(
            id=queue_id,
            status=Status.PENDING_QUEUE,
            client=client,
        )
        queue.append(q)
    
    emit_queue_stats()

    challenge = Challenge.generate(Config.POW_DIFFICULTY)
    session['challenge'] = str(challenge)

    return jsonify({'status': 'success', 'id': queue_id, 'challenge': str(challenge)})

@app.route('/screenshot/<id>')
def screenshot(id):
    filename = secure_filename(id)
    if not filename.endswith('.png'):
        filename += '.png'

    file_path = os.path.join(Config.SCREENSHOT_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return 'Screenshot not found!', 404

    return send_file(file_path, mimetype='image/png')

@app.route('/device_status')
def device_status():
    return jsonify({'status': 'success', 'device_ready': device_manager.is_device_ready()})

@app.errorhandler(413)
def too_large(e):
    return jsonify({'status': 'error', 'message': 'File too large!'}), 413

@socketio.on('connect')
def handle_connect(auth):
    emit_queue_stats()

@socketio.on('disconnect')
def handle_disconnect():
    pass

@socketio.on('join_queue')
def handle_join_queue(data):
    queue_id = data.get('queue_id')
    if not queue_id:
        emit('error', {'message': 'Queue ID is required'})
        return
    
    join_room(f'queue_{queue_id}')

@socketio.on('leave_queue')
def handle_leave_queue(data):
    queue_id = data.get('queue_id')
    if queue_id:
        leave_room(f'queue_{queue_id}')

@socketio.on('get_status')
def handle_get_status(data):
    queue_id = data.get('queue_id')
    if not queue_id:
        emit('error', {'message': 'Queue ID is required'})
        return
    
    with queue_lock:
        q = next((q for q in queue if q.id == queue_id), None)
    
    if q:
        emit_status_update(q)
    else:
        emit('error', {'message': 'Queue item not found'})

class QueueThread(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True

    def run(self):
        while self.running:
            try:
                with queue_lock:
                    pending = [q for q in queue if q.status == Status.PENDING_QUEUE]
                
                if pending:
                    for q in pending:
                        if not self.running:
                            break
                        self._process_queue(q)

                emit_queue_stats()
            except Exception as e:
                import traceback
                traceback.print_exc()

            time.sleep(5)

    def stop(self):
        self.running = False

    def _process_queue(self, q: Queue):
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._do_work, q)
                future.result(timeout=q.client.TIMEOUT)
        except TimeoutError:
            q.mark_error("Timeout! Please try again.")
            emit_status_update(q)
        except Exception as e:
            import traceback
            traceback.print_exc()
            q.mark_error('Error: ' + str(e))
            emit_status_update(q)

    def _do_work(self, q: Queue):
        chall_app = None
        poc_app = None

        q.update_status(Status.INITIALIZING)
        emit_status_update(q)

        chall_app = device_manager.device.application(q.client.PACKAGE_NAME)
        if not chall_app.is_installed():
            apk_path = os.path.join(os.getcwd(), Config.CHALLENGES_FOLDER, q.client.CHALLENGE_NAME, 'challenge.apk')
            if not os.path.exists(apk_path):
                raise Exception('Challenge APK file not found!')
            
            device_manager.device.upload_file(apk_path, '/data/local/tmp/challenge.apk')
            device_manager.device.install_local_file('/data/local/tmp/challenge.apk')
            device_manager.device.delete_file('/data/local/tmp/challenge.apk')

            if not chall_app.is_installed():
                raise Exception('Failed to install challenge APK!')

        q.update_status(Status.INSTALLING_POC)
        emit_status_update(q)

        apk_path = os.path.join(os.getcwd(), Config.UPLOAD_FOLDER, f'{q.id}.apk')
        if not os.path.exists(apk_path):
            raise Exception('POC APK file not found!')

        try:
            out, err = run_process('aapt', ['dump', 'badging', apk_path])
            if err:
                raise Exception('Invalid APK file!')

            match = re.search(r"package: name='(.*?)'", out)
            if not match:
                raise Exception('Invalid APK file!')

            package_name = match.group(1)
            if package_name == q.client.PACKAGE_NAME:
                raise Exception('Your POC cannot use the same package name as the challenge!')
        except Exception:
            raise Exception('Invalid APK file!')

        device_manager.device.upload_file(apk_path, '/data/local/tmp/poc.apk')
        device_manager.device.install_local_file('/data/local/tmp/poc.apk')
        device_manager.device.delete_file('/data/local/tmp/poc.apk')

        poc_app = device_manager.device.application(package_name)
        if not poc_app.is_installed():
            raise Exception('Failed to install POC APK!')

        if hasattr(q.client, 'callback') and q.client.callback:
            def update_status(status):
                q.update_status(status)
                emit_status_update(q)
            try:
                q.client.callback(poc_app, update_status)
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception('Something went wrong while testing your POC. This is a normal behavior and you should try again.')

        q.update_status(Status.TAKING_SCREENSHOT)
        emit_status_update(q)

        screenshot = device_manager.device.screenshot()
        screenshot.save(os.path.join(Config.SCREENSHOT_FOLDER, f'{q.id}.png'))

        q.mark_completed()
        emit_status_update(q)

        poc_app.uninstall()

if __name__ == '__main__':
    for client_file in glob.glob(os.path.join("challenges", "*", "client.py")):
        try:
            module_path = client_file.replace(os.sep, ".")[:-3]
            client = import_module(module_path)
            client.CHALLENGE_NAME = os.path.basename(os.path.dirname(client_file))
            clients.append(client)
        except Exception:
            pass

    # Start device monitoring
    device_manager.start_monitoring()
    
    # Start queue processing thread
    queue_thread = QueueThread()
    queue_thread.start()

    socketio.run(app, host='0.0.0.0', port=5000, debug=Config.DEBUG, allow_unsafe_werkzeug=True)