#!bin/bash
set -e
ROOT_NAME="<ROOT_FOLDER>"
WORKING_FOLDER_NAME="<WORKING_FOLDER_NAME>"
FILE_PREFIX="<FILE_PREFIX>"
FILE_EXTENSION=".dat"
SERVER_PATH="<SERVER_PATH>"
PASSWORD="<PASSWORD>"
BANDWIDTH_LIMIT="<BANDWIDTH_LIMIT>"
CIPHER_ALGORITHM="AES256"

FOLDER=${ROOT_NAME}"/"${WORKING_FOLDER_NAME}
FILE_NAME=${FILE_PREFIX}"-`date +%s`"
FINAL_NAME=${FILE_NAME}""${FILE_EXTENSION}

echo "$(date) $FILE_NAME Start"
echo "$(date) $FILE_NAME Archive"
cd ${FOLDER}
tar -cv * | gpg -c --cipher-algo ${CIPHER_ALGORITHM} --verbose --passphrase ${PASSWORD} -o ${ROOT_NAME}"/"${FINAL_NAME}
# zip -0 -P ${PASSWORD} -r $FILE_NAME *
# rar a -s -ep1 -m0 -hp${PASSWORD} $FILE_NAME *
cd ${ROOT_NAME}
echo "$(date) $FILE_NAME Upload"
rsync -Pha --bwlimit=${BANDWIDTH_LIMIT} ${FINAL_NAME} ${SERVER_PATH}
echo "$(date) $FILE_NAME Removing Sync folder content and file"
rm -rf ${FOLDER}/* ${FINAL_NAME}
echo "$(date) $FILE_NAME Finished"
