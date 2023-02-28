#!/bin/bash

read -p 'Enable logging (y/n)?' answer
if [ "$answer" = "${answer#[Yy]}" ] ;then
    bash -x ~/flash-tv-scripts/id_setup.sh
    bash -x ~/flash-tv-scripts/service_setup.sh
else
    bash ~/flash-tv-scripts/id_setup.sh
    bash ~/flash-tv-scripts/service_setup.sh
fi
