Nvidia-Container-toolkit 是 NVIDIA 提供的，能够让容器能访问宿主机 GPU 的一套工具。

><b>它解决的核心问题</b> ：宿主机 GPU 驱动等资源，是操作系统内核态的资源，无法打包进容器。容器中的 CUDA 程序没有使用 GPU 的运行环境。
>
>普通 docker 容器打包的是 「用户态fs + 应用程序 + 环境依赖」，它无法打包底层内核和驱动等底层的东西。即 docker 本身看不到 GPU。硬件驱动和本地操作系统高度绑定，是内核态的资源，无法放进 docker。docker 中的 CUDA 就没有运行环境。另外，换一个环境，可能硬件，驱动版本就变了，就与 docker 容器中的 CUDA 应用不匹配了，这让容器技术变得没有意义。

><b>解决方案</b>：容器内 CUDA 程序运行环境与宿主机 GPU 硬件分离。外部动态挂载，内部调用挂载资源的方式使用宿主机 GPU 硬件环境。
>
>把 docker 内 CUDA 应用程序运行的 GPU 执行环境，和 GPU 计算实际调用的资源(驱动，设备节点文件等)分离。资源不打包进容器。采用外部动态挂载，内部运行时环境调用调用挂载资源的方式，调用宿主机上的 GPU 设备完成工作。只要容器内部 GPU 运行时环境和外部驱动的版本匹配，容器内应用程序就可以正常运行。<u>容器内打包的执行运行环境是固定的，主要看外部挂载的资源是否配。</u>

容器使用(继承)宿主主机的内核，但是 <u>GPU 设备节点</u> `/dev/nvidia*`, <u>用户态驱动库</u> `libcudart.so`, 以及 <u>NVIDIA 的管理接口，默认都不在容器中。</u>

<u><b>CUDA Runtime</b></u> ： 容器中的 CUDA 应用，是运行在容器中的 CUDA Runtime 运行时环境上，执行 GPU 计算任务的。也就是说，容器中 CUDA 应用，需要 GPU 工作时，就通知 CUDA Runtime，由 CUDA Runtime 调用挂载在容器上的，宿主机内核中的 NVIDIA 驱动程序来执行具体计算。容器中的应用不会自己去直接调用 GPU 的底层资源。

这样就把容器内 CUDA 程序的运行环境，和实际需要调用的 GPU 资源分离了。只要宿主机的 GPU资源(包括驱动，设备文件等) 与容器中的 CUDA Runtime 的要求匹配，就可以把资源挂载到容器上，供 CUDA Runtime 调用。换一个环境，只要 CUDA Runtime 和 宿主机 GPU 硬件环境能匹配上，容器可以顺利运行。容器中的执行环境是固定的，主要看外部挂载的资源是否匹配。

CUDA runtime 运行时环境，通过运行时用户态库 `libcudart.so`(cudart, cuda runtime)向 CUDA 应用提供 CUDA Runtime API。CUDA Runtime 使用的用户态库`libcudart.so`，要和宿主机的GPU内核驱动版本严格匹配。

> 注意⚠️：Nvidia-Container-Toolkit 是安装在宿主机上的，它依赖 libnvidia-container 动态库来执行 GPU 资源挂载到容器的行为，`libnvidia-container.so` 动态库也是在宿主机上。容器中的运行时环境是通过 `libcudart.so` 向 CUDA 应用提供的 CUDA Runtime API。
> `libcudart.so` 才是运行时用户态库，它才是容器内的 CUDA Runtime 运行环境，是链接容器内环境与调用挂载的宿主机硬件资源的关键，<u>它必须和宿主机的GPU内核驱动版本严格匹配</u>。

# 1. Nvidia-Container-Toolkit 工作原理


> [!NOTE] Nvidia-Container-toolkit 简化工作流程
> `docker run` 命令调用常驻进程 dockerd 把容器构建出来。dockerd 调用 runc 构建程序来构建容器。我们注册一个 hook 到 dockerd 的配置上，让它在调用 runc 创建容器之前，触发这个hook。hook 的工作，就是调用 libnvidia-container 这个库，把宿主机上正确版本的驱动，设备节点等 nvidia 底层资源, 挂载到容器上。这样容器中的 CUDA Runtime 就可以调用它们完成工作。容器中只需安装 CUDA Runtime 运行时环境，不需要驱动，驱动程序始终是 CUDA Runtime 调用宿主机的那一份。


同一台机器上可以用不同 CUDA 版本的镜像（比如 vLLM 官方镜像带的是 CUDA 12.x），而宿主机只要装一个足够新的驱动就行，驱动程序版本是向下兼容 CUDA Runtime 的，即 驱动版本 ≥ 容器 CUDA runtime 要求就行。

Nvidia-Container-Toolkit 几个核心组件为：

> - `libnvidia-container`：底层 C 库，干实际挂载的活
> - `nvidia-container-toolkit`：把上面的库接到 OCI 流程里
> - `nvidia-ctk`：配置工具，在 dockerd 中进行一些 nvidia 配置, 比如 `nvidia-ctk runtime configure --runtime=docker` 会帮你改 `/etc/docker/daemon.json`，注册一个可选的nvidia-container-runtime 构建程序。

装好之后典型用法：

```bash
docker run --gpus all nvidia/cuda:12.4.0-base nvidia-smi
```

`--gpus all` 就是触发这套机制的开关，`all` 也可以换成 `--gpus '"device=0,1"'` ，指定启动的docker 容器进程，使用的是哪几张 GPU。

# 2. Nvidia-Container-toolkit 的安装与配置

nvidia-container-tookit 是安装在宿主机上的工具，我们在宿主机上先安装 nvidia-container-toolkit.

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

`sudo apt install -y nvidia-container-toolkit` 之前的部分是往 apt 中添加软件库的源。安装之后，执行 `sudo nvidia-ctk runtime configure --runtime=docker` , 会修改 `/etc/docker/daemon.json`, 这是把 nvidia runtime 注册进去。
注册之后，要`sudo systemctl restart docker` 重新启动 docker，dockerd 才能生效。

注意⚠️：`nvidia-container-toolkit` 中包含了 `nvidia-ctk` 配置工具，所以 `apt install nvidia-container-toolkit` 安装这个包之后，自然就有 nvidia-ctk 可以直接使用。但是 libnvidia-container 并不在安装包中。`libnvidia-container` → 它本体在独立的 `libnvidia-container1` 包里,**不在** toolkit 包内部,但 toolkit 包**依赖**它,所以 `apt` 会自动一并装上。
`nvidia-container-toolkit` 和 `libnvidia-container` 都不在Ubuntu官方源里，它们只在 NVIDIA 维护的仓库里发布，所以先把这个仓库添加到 apt 仓库源中，apt 才知道去哪儿拉这些包。

### Nvidia-Container-toolkit 发布地址

`nvidia-container-toolkit` 和 `libnvidia-container` 这两个包都在 `nvidia.github.io/libnvidia-container/` 这同一个仓库里发布。添加的就是这个源，`apt install nvidia-container-toolkit` 时，apt 从这个仓库里既能找到 `nvidia-container-toolkit` 本体，也能找到它依赖的 `libnvidia-container1`（以及 `libnvidia-container-tools`、`nvidia-container-toolkit-base` 等），一并解析、一并装上。不需要再加第二个源。所以上面只是把这个地址增加到了 apt 源中就够了。

这里库的命名上有个历史问题：仓库 URL 沿用了老项目名 `libnvidia-container`，但它现在发布的是<b><u>整条工具链的所有包</u></b>，不只是 `libnvidia-container1` 那一个库。所以名字看着像"只发布了这一个库"，实际整套工具都在里面。

# 3. 容器的构建过程

容器启动时，执行 `docker run` 真正把容器启动起来，要经过以下步骤。

```
docker (CLI)
   │  REST API (/var/run/docker.sock), 传递 "docker run" 命令
   ▼
dockerd (Docker daemon)         ← 管镜像、网络、卷、API
   │  gRPC
   ▼
containerd                      ← 容器生命周期管理器（高层 runtime）
   │
   ▼
containerd-shim                 ← 每个容器一个，守着容器进程
   │  exec
   ▼
runc                            ← 真正动手创建容器的低层 runtime 程序（OCI runtime）
   │  clone() + namespaces + cgroups + pivot_root
   ▼
你的容器进程（PID 1）
```

dockerd 接到 docker run 指令后，先调用 containerd，containerd 调用 runc 真正动手创建容器。
关键分界线在 **containerd 和 runc 之间**。习惯上把它们分两层：
- 「**高层 runtime（high-level）**」：containerd、CRI-O。管的是"宏观"的事——拉镜像、解包成 rootfs、准备网络和存储、调度容器生命周期。它**自己不直接创建容器**。
- 「**低层 runtime（low-level）**：runc、crun、gVisor、Kata。真正调 Linux 内核那套系统调用，把一个进程关进 namespace + cgroup 的"笼子"里。这一层就是 **OCI runtime**。
containerd 是高层runtime的部分，containerd-shim 是每个容器都有的一个负责低层 runtime 调用的部分，containerd 调用 containerd-shim 完成某一个具体容器的创建，如runc 等，才是真正的低层构建容器的 runtime 程序，或叫做 OCI Runtime。

# 4.  OCI 与OCI runtime

OCI = Open Container Initiative. 是 Docker 公司牵头，Linux基金会下成立的标准化组织。它是一个「标准规范」，用于规范容器和镜像的格式和行为。它主要有两个核心规范，「OCI Runtime Spec」和 「OCI Image Spec」。

「Runtime」: docker 语境下的 Runtime, 指的是容器运行时程序(如 `runc`, `crun`等)。被调用时，它负责把容器实例构建出来，成为内存中的容器进程，并且负责运行和管理它。因此，Runtime 是负责「创建并运行容器」的二进制可执行程序。

「OCI Runtime Spec」:  运行时规范标准。它给容器运行时程序在创建、启动、管理和销毁容器时应遵守的输入、状态和行为，制定了标准规范。例如，如何根据一个 OCI Bundle(容器在磁盘上的实体)，启动和管理容器进程。这个标准，规范的对象就是 Runtime，即「创建并运行容器」的二进制可执行程序。

> OCI Runtime Spec 包含：
> - filesystem bundle的格式：一个容器在磁盘上长什么样。它是一个目录，里面有解包好的rootfs(用户空间文件系统) 加一个 `config.json`。
> - `config.json` 非常关键，是容器的完整声明，用哪些 namespace、cgroup 限制多少 CPU/内存、挂载哪些路径、环境变量、要执行的命令、还有 **hooks**。
> - **命令行约定**：一个程序要想被称作 "OCI runtime"，必须实现一组标准子命令——`create`、`start`、`kill`、`delete`、`state`，参数和行为都按 spec 来。

「OCI Runtime」: 遵守 OCI Runtime Spec 规范的容器运行时程序，或「创建并运行容器」的二进制可执行程序。比如 `runc`, `crun`, `runsc`(gVisor, Google 的用户态内核沙箱), `kata-runtime` (轻量虚拟机)等，都是遵循 OCI Runtime Spec 标准规范的不同实现。他们可以互相替换，因为都尊循 OCI Runtime Spec 标准，接口一致。

> OCI Runtime 程序，给它一个 Bundle 目录(包含 config.json)，它就会调用 `runtime create <id>`, 照着 spec 把容器在内存中构建出来。 

「OCI Image Spec(镜像规范)」：定义容器镜像的格式规范。分层文件系统、manifest、config。管的是"镜像长什么样、怎么解包成 bundle"。和 runtime 互补，image spec 管静态的包，runtime spec 管把包跑起来。

从镜像到容器实例的构建过程，可简单描述为：

```
OCI 镜像
  ↓ 解包
OCI Bundle（config.json + rootfs）
  ↓
OCI Runtime（runc/crun）
  ↓
宿主机上的隔离进程
```

# 5. 容器实体

真正构建好了之后容器的物理实体，在系统中有两部分,「内存中跑的进程」和「磁盘上的内容」。
磁盘部分就是 `filesystem bundle`。

每个容器都独有一个自己的 bundle 目录，里面有 rootfs 和 config.json。它就是一个<u>待运行容器在磁盘上的完整形态</u>。runc 就是通过它来构建容器的。bundle 大概长这样：

```
/run/containerd/.../<container-id>/    ← bundle 目录
├── config.json      ← 这就是 OCI spec
└── rootfs/          ← 容器的根文件系统（解包好的镜像）
```


`config.json` 是「容器的完整说明书」— 把「怎么创建这个容器」的所有信息声明式地写在里面。
> config.json 就是 OCI Spec 的物理形态, 构建程序在构建容器时参考的文件。<u>有时我们也说容器的 OCI Spec 就是 config.json</u>。

另一部分就是内存中的容器进程。<u>如果容器销毁了(`docker rm`), 那么容器进程就销毁了，同时这个容器对应的磁盘上的 filesystem bundle 也就一并销毁，所以容器一停，bundle就销毁</u>。

# 6. containerd 和 runc 

Docker 创建容器实例时，默认由 containerd 调用 runc 来完成构建。<u>runc 就是一个遵守 OCI Runtime Spec 标准，实现的构建容器的可执行程序</u>。

构建容器的过程为，containerd 接受到 docker cli 传递过来的 docker run 命令后，根据此次传递过来的命令参数和 docker 镜像，containerd 会做以下几件事：

>1. 准备 rootfs (把镜像的只读层 + 一个可写层, 形成容器的根文件系统)
>2. 读镜像的 image config + 合并这次的运行时参数
>3. **生成 config.json**,连同 rootfs 一起组成 bundle,放进 `/run/containerd/.../<containerd-id>/`
>4. 调 runc (或在 Nvidia 场景里:先调 nvidia-container-runtime → 它改 config.json → 再调 runc)

所以 config.json 是<u><b>每次容器进入运行状态时"现生成的</b></u>。 `docker stop` 再 `docker start` 同一个容器,会**重新生成一份(因为它要重新进入运行状态)。


> [!NOTE] 容器构建的基本流程
> containerd 接受到 dockerd 传递过来的 docker run 命令，它会根据命令行参数和 image 的内容，生成容器 bundle，bundle 中含有 config.json，它就是 OCI Spec 的物理体现, 然后调用 runc, runc 只会根据 config.json 创建出容器进程。<u><b>runc 的行为 100% 由 config.json 决定</b></u>。同一个 runc 二进制程序,喂不同的 config.json, 就创建出完全不同的容器。runc 本身是"哑"的,它只是个忠实的执行器.
> 至此，容器创建完成，<u>内存中有一个容器进程，磁盘上有这个容器对应的 bundle</u>。

# 7. nvidia-container-runtime 

 runc 遵守的是 OCI runtime spec。它没有专门针对 nvidia GPU 驱动等资源进行处理的部分，如果直接使用 runc, 我们没法在容器启动的时候，挂载驱动等资源。所以, 如果要使用 GPU ，就要使用另一个二进制可执行程序来构建容器，就是 `nvidia-container-runtime`。

>nvidia-container-runtime 与 runc 一样，是一个负责容器创建和运行的二进制可执行程序，也遵循 OCI Runtime Spec。

### 注册二进制构建程序 nvidia-container-runtime
 
 nvidia-container-runtime 是另一个容器构建程序，Docker 默认使用的是 runc, 我们需要把这个构建程序注册在 dockerd 中，让它知道可以使用  nvidia-container-runtime 这个二进制来构建容器。我们要把这个程序注册在 `/etc/docker/daemon.json`中. 注册之后，dockerd 就知道在特定情况下可以调用 nvidia-container-runtime 来创建容器，而不是默认的 runc. 
 注册的时候我们使用的是
 
 ```bash
 sudo nvidia-ctk runtime configure --runtime=docker
 ```

`nvidia-ctk` 是 nvidia-container-toolkit 中包含的配置工具。这条命令执行后，它就会自动修改 `/etc/docker/daemon.json`, 把 nvidia-container-runtime 注册进去，完成"登记"。`nvidia-ctk runtime configure --runtime=docker` 这行命令会往 `daemon.json` 新增写入这么一段

```json
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
```

注意，这是在 runtimes 中增加了一个名叫 nvidia 的可选 runtime，并没有动 `default-runtime`（默认仍是 `runc`）。只是登记了一个备选项。
注册之后，`sudo systemctl restart docker` 重新启动 docker，就会生效。

# 8. OCI Spec 注入

注册完成，当我们使用`docker run --gpus all` 这个参数的时候，dockerd就会调用 nvidia-container-runtime 来构建容器。

首先，dockerd/containerd 合并生成相应的容器 bundle，包括 OCI Spec，即容器的 `config.json`
然后，调用 nvidia-container-runtime 来构建容器。

nvidia-container-runtime 所做的工作就是把容器的`config.json` 读取进来，然后往 `hooks.prestart`里面塞一条记录：

```json
"hooks": {
  "prestart": [
    {
      "path": "/usr/bin/nvidia-container-runtime-hook",
      "args": ["nvidia-container-runtime-hook", "prestart"]
    }
  ]
}
```

改完, 再把修改后的 spec 交给 runc。<u>最终还是调用 runc 来完成构建容器</u>。 runc 读到的 `config.json`已经带着这条 hook 了,它执行到 `run_hooks(spec.hooks.prestart)` 那一步时,就会去跑 `nvidia-container-runtime-hook`—— GPU 挂载行为就此发生。

>所谓「注入」，就是`nvidia-container-runtime` 执行时先修改了 config.json, 往里面追加一个hook条目。然后再调用 runc。runc 执行过程中就会执行到 config.json 文件里面追加的那个 hook。这个过程就相当于往 runc 里面注入了额外的步骤。而`nvidia-container-runtime-hook`做的事就是调用`libnvidia-container` 这个 `.so` 库来完成挂载工作。

这个过程有点像设计模式中的装饰器模式，在runc前面增加一个 OCI 的注入操作，就形成了装饰器，nvidia-container-runtime 程序。执行它的时候，就是先执行注入操作，再调用 runc。
runc 是在 config.json 文件中读取到hook后，去执行这个 hook 程序，`nvidia-container-runtime-hook`， 这个 hook 程序再调用`libnvidia-container`这个库来进行驱动程序和其他资源的挂载，完成后，runc 再继续进行后续的容器构建工作。  


> [!NOTE] 总结
> - nvidia-container-tookit 解决的是包含 CUDA 的 docker 容器只能打包用户空间的环境的问题。对于GPU，容器中最多有 CUDA Runtime。但是 CUDA Runtime 要依赖驱动，容器无法打包内核驱动。只有 CUDA runtime 和驱动严格匹配，CUDA程序才能正确执行。
> <br>
> - 所以，就把驱动等宿主资源，在容器启动的时候，挂载到容器上。这个机制使得 CUDA 应用在容器中可以使用 CUDA Runtime 运行，只和容器内的环境有关，与外部环境无关。CUDA Runtime 可以在不同的宿主机上调用不同挂载上来的 nvidia 驱动完成工作。这就使得容器可以在任何环境中运行，只要 CUDA Runtime 和 驱动能匹配就行。
>  <br>
> - 它的运行原理是，Docker 在构建容器时，传入 --gpus all 的参数，就不用默认的 runc 来构建容器，而使用经过注册的 nvidia-container-runtime 程序来构建容器。nvidia-container-runtime 本质上还是调用 runc 来完成工作，不过在调用 runc 之前，通过 OCI Spec 注入的方式，增加一个 prestart 的 hook, 具体做法就是修改容器 bundle 中的 `config.json`文件，增加一个hook。然后再调用 runc。runc 看到hook以后就会先去(这就是prestart)调用hook指向的程序，`nvidia-container-runtime-hook`，这个程序就会通过 `libnvidia-container`库(.so)，把驱动挂载到容器上，然后执行 runc 后续工作，完成容器的构建。这就是 nvidia-container-tookit 的基本原理。


