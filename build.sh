#!/bin/bash
# Script to synchronize source and build Debian package

# Define variables
SOURCE_FILES="ut_api.py ut_app.py ut_engine.py"
PKG_DIR="packaging"
DEST_DIR="$PKG_DIR/usr/lib/python3/dist-packages/utoop_music"

# Extract package name and version from control file
PKG_NAME=$(grep -E "^Package:" $PKG_DIR/DEBIAN/control | cut -d' ' -f2)
VERSION=$(grep -E "^Version:" $PKG_DIR/DEBIAN/control | cut -d' ' -f2)
ARCH="all"
OUTPUT_DEB="${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo "Synchronizing source files to packaging directory..."
cp $SOURCE_FILES $DEST_DIR/

echo "Building Debian package..."
dpkg-deb --build $PKG_DIR

# Rename the output to standard Debian format
mv "$PKG_DIR.deb" "$OUTPUT_DEB"

echo "Build complete: $OUTPUT_DEB"
