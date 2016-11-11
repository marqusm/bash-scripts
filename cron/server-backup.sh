#!/usr/bin/env bash
set -e

# Params
DESTINATION=/var/backup

# Constants
SVN_FOLDER=/srv/svn

# Variable
TIMESTAMP=$(date +"%Y-%m-%d--%H-%M")
TEMP_FOLDER=${DESTINATION}/backup-${TIMESTAMP}
OUTPUT_FILE=${DESTINATION}/server.${TIMESTAMP}.backup.tar.gz

echo "backup started"
echo "time: "$(date)
echo "destination folder: "${DESTINATION}

if [ ! -d "${DESTINATION}" ]; then
    echo "creating destination folder..."
    mkdir ${DESTINATION}
fi

mkdir ${TEMP_FOLDER}
mkdir ${TEMP_FOLDER}/svn
echo "coping files..."

for d in ${SVN_FOLDER}/*/ ; do
    svnadmin dump ${d} > ${TEMP_FOLDER}/svn/$(basename ${d}).svn.dump
done

echo "archiving..."
cd ${TEMP_FOLDER}
tar -czf ${OUTPUT_FILE} *

echo "removing temp files..."
rm -rf ${TEMP_FOLDER}

echo "done. created file "${OUTPUT_FILE}"."
