#!/bin/bash

function kill_adb() {
  echo "[i] Killing ADB..."
  pkill -f "adb.*server" 2>/dev/null
  sleep 2
  pkill -9 -f "adb.*server" 2>/dev/null
};

function start_adb() {
  echo "[i] Starting ADB..."
  nohup adb -a -P 5037 nodaemon server > adb.log 2>&1 &
};

function kill_emulator() {
  echo "[i] Killing emulator..."
  pkill -f "qemu-system-x86_64.*${EMULATOR_NAME}" 2>/dev/null
  sleep 2
  pkill -9 -f "qemu-system-x86_64.*${EMULATOR_NAME}" 2>/dev/null
}

function start_emulator() {
  echo "[i] Starting emulator..."

  accel_option=""

  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [[ $(egrep -c '(vmx|svm)' /proc/cpuinfo) -gt 0 ]]; then
      accel_option="-accel on"
    else
      accel_option="-no-accel"
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    accel_option="-accel on"
  elif [[ "$OSTYPE" == "msys" ]]; then
    accel_option="-accel hax"
  else
    accel_option="-no-accel"
  fi

  nohup emulator -avd "$EMULATOR_NAME" -writable-system -no-window -noaudio -no-boot-anim -memory $MAX_MEMORY $accel_option > emulator.log 2>&1 &
};

function wait_for_device() {
  echo "[i] Waiting for device..."
  adb wait-for-device
  while [ "$(adb get-state)" == "offline" ]; do
      sleep 1
  done
};

function start_device() {
  start_emulator
  wait_for_device

  if [ "$1" == "true" ]; then
    echo "[i] Disabling security..."

    adb root
    sleep 2.5

    adb shell avbctl disable-verification
    adb disable-verity

    echo "[i] Rebooting device..."
    adb reboot

    wait_for_device
  fi

  while [ "$(adb shell getprop sys.boot_completed 2>&1)" != "1" ]; do
      sleep 1
  done

  echo "[i] Device booted!"

  echo "[i] Setting up device..."

  adb root
  sleep 2.5

  echo "[i] Mounting system..."

  adb remount
  sleep 2.5

  echo "[i] Setting up lamda..."

  adb push lamda-server-x86_64.tar.gz /data
  adb shell tar -zxf /data/lamda-server-x86_64.tar.gz -C /data
  adb shell chmod +x /data/server/bin/launch.sh
  adb shell "cd /data/server/bin; ./launch.sh"
  adb forward tcp:65010 tcp:65000
  nohup socat TCP-LISTEN:65000,bind=0.0.0.0,reuseaddr,fork TCP:127.0.0.1:65010 > socat.log 2>&1 &

  echo "[i] Locking 'su' binary..."

  adb shell chown root:shell /system/xbin/su
  adb shell chmod 6750 /system/xbin/su

  echo "[i] Disabling virtual keyboard..."

  adb shell pm disable-user com.google.android.inputmethod.latin
  adb shell pm disable-user com.google.android.tts
  adb shell pm disable-user com.google.android.googlequicksearchbox

  echo 1 > /app/device_ready
  echo "[i] Device is ready!"
};

function main() {
  kill_adb
  start_adb
  kill_emulator
  start_device true

  while true; do
    if ! pgrep -f "qemu-system-x86_64.*${EMULATOR_NAME}" > /dev/null; then
      echo "[i] Main emulator process not running, restarting emulator..."
      kill_emulator
      sleep 2.5
      start_device false
    fi

    if ! pgrep -f "adb.*server" > /dev/null; then
      echo "[i] ADB server not running, restarting emulator..."
      kill_emulator
      sleep 2.5
      start_device false
    fi

    local connected_devices=$(adb devices | grep emulator | grep device | wc -l)
    if [[ $connected_devices -eq 0 ]]; then
      echo "[i] No devices connected, restarting emulator..."
      kill_emulator
      sleep 2.5
      start_device false
    else
      local device_id=$(adb devices | grep emulator | grep device | head -n1 | cut -f1)
      if ! timeout 10 adb -s "$device_id" shell echo "test" > /dev/null 2>&1; then
        echo "[i] Device unresponsive, restarting emulator..."
        kill_emulator
        sleep 2.5
        start_device false
      fi
    fi

    if ! timeout 5 curl -s --connect-timeout 3 http://localhost:65000 > /dev/null 2>&1; then
      echo "[i] Lamda service not responding, restarting emulator..."
      kill_emulator
      sleep 2.5
      start_device false
    fi

    sleep 5
  done
};

main
