#!/bin/bash
# Simple script to create properly sized icons from favicon

cd "$(dirname "$0")"

# Create 144x144 icon from 256px favicon
cp ../favicon-256.png icon-144x144.png

echo "Icon fix applied - using 256px favicon for 144x144"
echo "For proper resizing, use:"
echo "  brew install imagemagick"
echo "  convert ../favicon-256.png -resize 144x144 icon-144x144.png"