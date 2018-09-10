#!/usr/bin/env bash

hosts=${@:-$(echo rejh{1,2}.srv.releng.{mdc1,mdc2}.mozilla.com)}

# 1. log into all first to open connections with mfa
# This expects ssh_config ControlPersist to be set (for long enough to keep
# the connection alive until the last one runs).

# 2. step through each with puppet

for host in ${hosts}; do
    ssh "${host}" "uptime"
done

echo "Restart Script starting in 10 seconds"
sleep 7s

echo "Restart Script starting in 3 seconds"
sleep 3s

python3 modules/ssh_restart_osx.py
