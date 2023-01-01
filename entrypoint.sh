#!/bin/bash

# Entrypoint script for Python+Chrome container.
# Sets CHROME_VERSION environmental variable.
# Starts Xvfb screen and runs a background loop that keeps it running.
# Executes input argument command.


# Set CHROME_VERSION environmental variable
chrome_version=$(google-chrome --version | grep -Po "\\d+" | head -1)
export CHROME_VERSION=$chrome_version
# Alternative: chrome_version=$(google-chrome --version | sed 's/Google Chrome \([0-9]*\).*/\1/g')

# Start Xvfb and keep it running
function keep_up_screen()
{
    while true; do
        sleep 1
        if [ -z "$(pidof Xvfb)" ]; then
            Xvfb "$DISPLAY" -screen "$DISPLAY" 1280x1024x16 &
        fi
    done
}

keep_up_screen &

# Execute input argument as command
exec "$@"
