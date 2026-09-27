#!/bin/bash
set -euo pipefail

distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
echo $distribution

# 将官方的libnvidia-containder的GPG 添加进 apt 信任的 GPG
# key，放在/usr/sharing/keyrings/中
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --yes --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 将libnvidia-container 和nvidia-container-toolkit 的源添加到 apt 的软件仓库源中
# 这两个包都在nvidia.github.io/libnvidia-container/下面的，所以只需把这个地址，添加到apt源中就可以了。
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
	sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
	sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list


sudo apt update
sudo apt install -y nvidia-container-toolkit

# 将 nvidia-container-runtime 注册到daemon.json中，供dockerd 在创建容器时调用
sudo nvidia-ctk runtime configure --runtime=docker 

sudo systemctl restart docker

# 验证
docker run -rm --gpus all nvidia/cuda:13.0.0-base-ubuntu22.04 nvidia-smi

