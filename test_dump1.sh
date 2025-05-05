#!/bin/bash

if [ -z "$DATE" ]; then
    echo "Error: DATE environment variable is not set"
    echo "Usage: DATE=your_date ./test_dump1.sh"
    exit 1
fi

sleep 2
echo "restore 1 - $DATE"
sleep 2
echo "restore 2 - $DATE"

# Change to the specified directory and find files
cd /Users/ngodanghuy/KLTN/test
find . -type f -name "*$DATE*" -exec cat {} \;
