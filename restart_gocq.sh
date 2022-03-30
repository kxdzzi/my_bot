echo "重启$1"
screen -ls|awk '/'$1'/{print "screen -S "$1" -X quit"}'|sh
screen -dmS $1 bash -c "cd /home/ubuntu/go-cqhttp/$1;./go-cqhttp faststart"
echo "重启成功"