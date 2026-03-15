#!/usr/bin/bash
set -e

############################################################
# Params
############################################################
SOURCE_PORT="<PORT>"
SOURCE="<SOURCE>"
DESTINATION="<DESTINATION>"
HI_SPEED_LIMIT=10000
LOW_SPEED_LIMIT=10000
EXCLUDE_TEMP_FILES=TRUE
REMOVE_SOURCE_FILES=FALSE
TIMEOUT=10000 # 900 for 15mins and 1200 for 20 mins
LOGGING=TRUE

############################################################

# Check if already running
RCLONE_OCCURANCES=
RCLONE_OCCURANCES=$(ps -ax | grep "rclone" | wc -l)
if [ $RCLONE_OCCURANCES -gt 1 ]
then
    echo "Sync script is already running. Running time:"${RUNNING_TIME}"s. Skipping."
    exit 1
fi

# Variables
START_DATE=
START_DATE_S=
END_DATE_S=
DURATION=

TIME_HOURS=$(eval date +"%H")
if [ ${TIME_HOURS} -gt 23 ] && [ ${TIME_HOURS} -lt 6 ]
then SPEED_LIMIT=${HI_SPEED_LIMIT}
else SPEED_LIMIT=${LOW_SPEED_LIMIT}
fi

RCLONE_COMMAND="rclone copy outlander:downloads/complete/ /mnt/data/marko/Downloads/Outlander -P --transfers=1 --checkers=1 --multi-thread-streams=0 -

# Run the command
START_DATE=$(date)
START_DATE_S=`date +%s`
echo "Sync started @ "${START_DATE}
#echo ${RCLONE_COMMAND}
eval ${RCLONE_COMMAND}
END_DATE=$(date)
END_DATE_S=`date +%s`
DURATION=$((END_DATE_S-START_DATE_S))
echo "Sync completed in "${DURATION}" seconds"

exit 0
