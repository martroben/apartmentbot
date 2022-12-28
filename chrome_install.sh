#!/bin/sh
# Install latest stable version of Chrome in Docker container

export DEBIAN_FRONTEND=noninteractive && \
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub > /usr/share/keyrings/chrome.pub && \
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/chrome.pub] http://dl.google.com/linux/chrome/deb/ stable main' > \
/etc/apt/sources.list.d/google-chrome.list && \
apt update -y && \
apt install -y google-chrome-stable
