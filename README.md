
# 安装python3.9
sudo apt update

sudo apt install software-properties-common

sudo add-apt-repository ppa:deadsnakes/ppa

sudo apt install python3.9

sudo apt-get install python3-tk

git clone https://github.com.cnpmjs.org/ermaozi/mini_jx3_bot.git

docker -v  2> /dev/null|| curl -sSL https://get.daocloud.io/docker | sh


docker run  --name="mongo"  -p27017:27017 -p28017:28017 -v /docker-data/mongo:/data/db -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=pwd  -d mongo


原项目地址: https://github.com/JustUndertaker/mini_jx3_bot

