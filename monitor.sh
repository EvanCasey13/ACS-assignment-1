#!/usr/bin/bash
#
# Some basic monitoring functionality; Tested on Amazon Linux 2
#
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
DISKUSAGE=$(df -h | awk '$NF=="/"{printf "%s\t\t", $5}')
CPU_USAGE=$(top -bn1 | grep load | awk '{printf "%.2f%%\t\t\n", $(NF-2)}')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)

echo "Instance ID: $INSTANCE_ID"
echo "Memory utilisation: $MEMORYUSAGE"
echo "Disk Usage: $DISKUSAGE"
echo "CPU Usage: $CPU_USAGE"
echo "Ip: $PUBLIC_IP"
echo "No of processes: $PROCESSES"
if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi

