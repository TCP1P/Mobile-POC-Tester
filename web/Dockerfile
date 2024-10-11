FROM python:3.9-slim

RUN apt update && apt install -y --fix-missing curl wget unzip build-essential python3 python3-pip android-tools-adb android-tools-fastboot aapt
RUN pip3 install flask pycryptodome waitress

WORKDIR /app
COPY . .

WORKDIR /app/src
EXPOSE 5000
CMD ["python3", "app.py"]
