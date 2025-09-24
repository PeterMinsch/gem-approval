#!/bin/bash

# Chrome Dependency Installation Script
echo "🔧 Installing missing Chrome dependencies..."

# Update package list
sudo apt update

# Install the 3 missing dependencies identified by diagnostic
echo "📦 Installing libgconf-2-4..."
sudo apt install -y libgconf-2-4

echo "📦 Installing libappindicator1..."
sudo apt install -y libappindicator1

echo "📦 Installing libindicator7..."
sudo apt install -y libindicator7

# Install additional Chrome dependencies that are commonly needed
echo "📦 Installing additional Chrome dependencies..."
sudo apt install -y \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6

echo "✅ Chrome dependencies installation complete!"
echo "🔄 Now restart your bot to test the fix."