screen -S mybot -X quit;screen -dmS mybot bash -c 'cd ~/mini_jx3_bot;git pull;python3.9 bot.py'

for i in $(ls ~/go-cqhttp/);do
    screen -S $i -X quit;screen -dmS $i bash -c "cd ~/go-cqhttp/$i;./go-cqhttp faststart"
done

screen -dmS update bash -c 'cd ~/mini_jx3_bot;python3.9 server_update.py'