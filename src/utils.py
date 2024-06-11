from subprocess import Popen, PIPE

def run_process(process, args):
    process = Popen([process] + args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate(timeout=30)
    return stdout.decode('utf-8'), stderr.decode('utf-8')
