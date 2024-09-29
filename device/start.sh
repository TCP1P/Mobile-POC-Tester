#!/bin/bash

function kill_emulator() {
  adb devices | grep emulator | cut -f1 | xargs -I {} adb -s "{}" emu kill
};

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

  emulator -avd "$EMULATOR_NAME" -writable-system -no-window -noaudio -no-boot-anim -memory 2048 $accel_option &
};

function wait_for_device() {
  echo "[i] Waiting for device..."

  adb wait-for-device

  while [ "$(adb get-state)" == "offline" ]; do
      sleep 1
  done
};

function start_device() {
  echo "[i] Starting device..."

  adb -a -P 5037 nodaemon server 2>&1 > /dev/null &
  sleep 2.5

  kill_emulator
  start_emulator
  wait_for_device
  
  echo "[i] Disabling security..."

  adb root
  sleep 2.5

  adb shell avbctl disable-verification
  adb disable-verity

  echo "[i] Rebooting device..."
  adb reboot

  wait_for_device

  while true; do
      result=$(adb shell getprop sys.boot_completed 2>&1)

      if [ "$result" == "1" ]; then
          break
      fi

      sleep 1
  done;

  echo "[i] Initializing device..."

  adb root
  sleep 2.5

  echo "[i] Mounting system..."

  adb remount
  sleep 2.5

  adb shell mv /system/xbin/su /system/xbin/su-48916722dabda77a42e59b85751e81bf
  adb shell chmod 711 /system/xbin

  echo "[i] Device is ready!"
};

function main() {
  start_device

  while true; do
    if [[ $(ps aux | grep emulator | grep -v grep | wc -l) -eq 0 ]]; then
      echo "[i] Emulator is not running, restarting emulator..."

      start_device
    fi

    if [[ $(adb devices | grep emulator | wc -l) -eq 0 ]]; then
      echo "[i] Device is not connected, restarting emulator..."
      
      kill_emulator

      sleep 2.5

      start_device
    fi

    if [[ $(ps aux | grep adb | grep -v grep | wc -l) -eq 0 ]] || [[ $(lsof -i :5037 | grep LISTEN | wc -l) -eq 0 ]]; then
      echo "[i] ADB is not running, restarting ADB..."

      adb kill-server

      sleep 2.5

      adb -a -P 5037 nodaemon server 2>&1 > /dev/null &
    fi

    sleep 5
  done;
};

main