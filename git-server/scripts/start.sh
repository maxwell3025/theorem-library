#!/bin/sh
/generate_repos.sh
spawn-fcgi -s /var/run/fcgiwrap.socket -M 666 /usr/bin/fcgiwrap
nginx -g "daemon off;"