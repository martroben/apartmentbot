#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

# Script to install a certain version of Chrome.
# Might be desirable in scraping, because using latest version of Chrome
# makes the scraper more easily identifyable as a bot.
# (Not a lot of real users have the latest browser version.)
# Usage: ./chrome_install [version_number]

# Get the Chrome version from arguments (default: 107)
version_main=${1:-107}

# List of full version numbers
# https://www.ubuntuupdates.org/package/google_chrome/stable/main/base/google-chrome-stable?id=202706
available_versions=("105.0.5195.125-1" "106.0.5249.119-1" "107.0.5304.121-1" "108.0.5359.124-1")

# Match full version number
for version in "${available_versions[@]}"; do
    if [[ $version =~ ^"$version_main" ]]; then
        chrome_version=$version
    fi
done

# Install Chrome
chrome_link=dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${chrome_version}_amd64.deb
wget -q -O /tmp/chrome.deb "${chrome_link}"
apt update -y
apt install -y /tmp/chrome.deb
rm /tmp/chrome.deb
