import subprocess
import re
import os
from time import sleep
from typing import Tuple
from config import Config

def run_process(process: str, args: list, timeout: int = 30) -> Tuple[str, str]:
    args = [process] + args
    
    try:
        result = subprocess.run(
            args, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            timeout=timeout,
            text=True
        )
        return result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        return "", f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return "", f"Command not found: {process}"
    except Exception as e:
        return "", str(e)

def run_adb(args: list, timeout: int = 30) -> Tuple[str, str]:
    if Config.DEBUG:
        return run_process('adb', args, timeout)
    
    return run_process('adb', ['-H', 'device', '-P', '5037'] + args, timeout)