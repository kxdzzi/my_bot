sudo docker restart mongo
echo 数据库重启成功
screen -S my_bot -X quit;screen -dmS my_bot bash -c 'cd ~/my_bot;git pull;python3.9 bot.py'
echo 框架重启成功

screen -dmS update bash -c 'cd ~/my_bot;python3.9 server_update.py'
echo 重启成功!
