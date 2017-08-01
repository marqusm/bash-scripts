#!/usr/bin/env bash
set -e

# Params
SERVER_SOURCE_PATH="<SERVER_SOURCE_PATH>"
CLIENT_SOURCE_PATH="<CLIENT_SOURCE_PATH>"
MEDIA_SOURCE_PATH="<MEDIA_SOURCE_PATH>"

DESTINATION_PATH="<DESTINATION_PATH>"
CLIENT_DESTINATION_PATH="<CLIENT_DESTINATION_PATH>"

ARTIFACT_NAME="<ARTIFACT_NAME>"

# Build server
cd ${SERVER_SOURCE_PATH}
git pull
mvn clean package

# Build client
cd ${CLIENT_SOURCE_PATH}
git pull
rm -rf node_modules
npm install
npm run build

# Copy and restart server
if [ ! -d "${DESTINATION_PATH}" ]; then
    mkdir ${DESTINATION_PATH}
fi
cp ${SERVER_SOURCE_PATH}/target/${ARTIFACT_NAME} ${DESTINATION_PATH}/${ARTIFACT_NAME}
service legal-assistant restart

# Copy client
if [ ! -d "${CLIENT_DESTINATION_PATH}" ]; then
    mkdir ${CLIENT_DESTINATION_PATH}
fi
cp -r index.html public/ vendor/ css/ ${CLIENT_DESTINATION_PATH}
cd ${MEDIA_SOURCE_PATH}
cp -r font image media ${CLIENT_DESTINATION_PATH}
