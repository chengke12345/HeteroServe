Nvidia-Conainer-Toolkit 是安装在宿主机上的工具，它的作用是在 Docker 镜像构建成 Docker 容器的时候，通过注入构建程序的方式，调用 `libnvidia-container.so` 库，将宿主机的 Nvidia GPU 驱动挂载到容器中去。而容器中只保留驱动的运行时环境 CUDA Runtime，就可以调用任意与Runtime 兼容的驱动去完成GPU计算。

# 1. 首先安装 Docker

```bash
curl -fsSL https:// get.docker.com | sh
sudo usermode -aG docker $USER
newgrp docker
```

# 2.  安装 Nvidia-Container-Toolkit

在宿主机上，执行以下脚本完成安装
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --yes --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
	sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
	sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
```

采用 GPG 的加密验证方式，将官方 libnvidia-container 的 GPG 放入 apt 信任列表中，然后添加 apt 源，通过 apt 下载 `Nvidia-Container-Toolkit`,  下载这几个软件包

![](/docs/assets/nvidia-container-toolkit-assets/Pasted%20image%2020260813063115.png)

# 3. 注册 nvidia-container-runtime

安装完成后，需要将 nvidia-container-runtime 二进制容器构建程序注册到 dockerd(docker daemon) 的配置文件 daemon.json 中，让 dockerd 在创建容器时调用。

```bash
sudo nvidia-ctk runtime configure --runtime=docker 
sudo systemctl restart docker
```

使用 nvidia-container-toolkit 中包含的工具 nvidia-ctk 自动把 runtime 注册到 docker 中，然后重启 docker 完成更新。

# 4. 验证

使用 `nvidia-ctk --version` 可以查看当前系统中 Nvidia-Container-Toolkit 的版本，如果安装正确，应该能够看到
![](/docs/assets/nvidia-container-toolkit-assets/Pasted%20image%2020260813072548.png)

如果正常注册了 nvidia-container-runtime, 那么可以通过 `docker info | grep -i - E 'Runtimes|Default runtime'` 查看，可以看到列表里，除了默认的 runc 之外，还多了一个 nvidia 的可选构建程序。

![](/docs/assets/nvidia-container-toolkit-assets/Pasted%20image%2020260813072328.png)

nvidia-container-runtime 注册成功以后，可以通过 Nvidia 官方通用的 CUDA 镜像 `cuda:13.0.0-base-ubuntu22.04`，验证宿主机环境，是否能够正确挂载本地驱动和设备文件
```bash
docker run --rm --gpus all docker.io/nvidia/cuda:13.0.0-base-ubuntu22.04 \
nvidia-smi
```

`--rm` : 表示容器验证完之后，就删除容器。
`--gpus all` : 表示把宿主机的 GPU，全部提供给容器。当然，这里也可以提供 `cuda:0,1`  ，表示把0，1号 GPU 提供给容器。
`docker.io/...`: 表示用于测试 Nvidia CUDA 的镜像
`nvidia-smi`: 表示进入容器后执行的命令

完整的验证链路为
```
宿主机驱动 → NVIDIA Container Toolkit → Docker → 容器内 GPU

CUDA 测试镜像
    ↓ 请求 --gpus all
宿主机 NVIDIA Container Toolkit
    ↓ 挂载 GPU 设备和驱动组件
宿主机 NVIDIA 驱动与 GPU
```

如果一切正常，会看到 CUDA 基础容器中，用 nvidia-smi 命令，通过挂载的驱动，可以读取到宿主机 GPU 的信息，本机是三张 2080ti GPU。

![](/docs/assets/nvidia-container-toolkit-assets/Pasted%20image%2020260813075746.png)

看到这个画面说明 Nvidia-Container-Toolkit 已经安装成功了。