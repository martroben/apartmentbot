#!/bin/bash
# Entrypoint script of the Python/Chrome docker container.

# Get chrome version and assign it as an environmental variable
# (Can be used to download the correct chromedriver version.)
chrome_version=$(google-chrome --version | sed 's/Google Chrome \([0-9]*\).*/\1/g')
export CHROME_VERSION=$chrome_version


function keep_up_screen()
# Checks if Xvfb is up every 1 seconds and starts it if not
{
    while true; do
        sleep 1
        if [ -z "$(pidof Xvfb)" ]; then
            Xvfb "$DISPLAY" -screen "$DISPLAY" 1280x1024x16 &
        fi
    done
}

# Run in background
keep_up_screen &

# Run argument as the main command in the container
# sudo docker run --rm container --this part--> python3 file.py
exec "$@"
