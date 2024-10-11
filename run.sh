#!/bin/bash
cat <<EOF > .env
SU_NAME=su-$(head -c 16 /dev/urandom | xxd -p | tr -d '\n')
EOF

sudo docker compose up --build --force-recreate -d
