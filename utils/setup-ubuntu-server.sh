#!/usr/bin/env bash

# Set update alias
sudo echo "" >> /etc/bash.bashrc
sudo echo "# -------" >> /etc/bash.bashrc
sudo echo "# Aliases" >> /etc/bash.bashrc
sudo echo "# -------" >> /etc/bash.bashrc
sudo echo "alias update=\"sudo apt-get update && sudo apt-get -y upgrade && sudo apt-get -y dist-upgrade && sudo apt-get -y autoremove\"" >> /etc/bash.bashrc

# Make history work
sudo echo "" >> /etc/inputrc
sudo echo "\"\e[A\": history-search-backward" >> /etc/inputrc
sudo echo "\"\eOA\": history-search-backward" >> /etc/inputrc
sudo echo "\"\e[B\": history-search-forward" >> /etc/inputrc
sudo echo "\"\eOB\": history-search-forward" >> /etc/inputrc

# Install Joe
sudo apt install -y joe
