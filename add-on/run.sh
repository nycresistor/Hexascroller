#!/usr/bin/with-contenv bashio
#
# Script to start Hexascroller hexaservice
#

set -euo pipefail

sleep 2
ls /dev/ttyACM*
lsof /dev/ttyACM*

# Check if debug is enabled and set the debug environment variable
if bashio::config.true 'debug'; then
    debug_env="--debug --debug-host \"$(bashio::config 'debug_host')\""
else
    debug_env=""
fi

# Start the hexaservice with the MQTT configuration and the debug environment variable
cd /app/Hexascroller/hexaservice

exec nice -10 python3 service.py $debug_env \
    --mqtt-host="$(bashio::services mqtt 'host')" \
    --mqtt-user="$(bashio::services mqtt 'username')" \
    --mqtt-password="$(bashio::services mqtt 'password')"
