#!/usr/bin/env bash
./cvat-cli mass_create --labels labels-tram.json --image-quality 90 --frame-filter "step=2" share videos.json