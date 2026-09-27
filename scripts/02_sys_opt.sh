#!/bin/bash
set -euo pipefail
#1. swap 配置（NVME上32GB）
sudo fallocate -l 32GB /swapfile # 预分配一个32Gb 大小的文件 /swapfile 作为Linux的交换分区，预分配不是真分配，标记好文件，不写数据
sudo chmod 600 /swapfile         # 权限限制，只允许 root 读写
sudo mkswap /swapfile            # 把这个文件格式化为 swap结构
sudo swapon /swapfile            # 激活swap
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab # 往/etc/fstab中添加一行，开机自动挂载。

#2. sysctl 调优
sudo tee /etc/sysctl.d/99-vllm.conf << 'EOF'

# swap 倾向：尽量不用swap, 仅加载时使用
vm.swappiness=1

# 允许内存超额分配(fork大进程必须)
vm.overcommit_memory=1

# 文件缓存压力降低
vm.vfs_cache_pressure=50

#网络性能
# 高并发http 服务监听队列
net.core.somaxconn=65535 
net.ipv4.tcp_max_syn_backlog=65535
EOF
sudo sysctl --system

# 3. Transparent Huge Pages（VLLM 推荐）
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag

# 关闭THP的持久化
sudo tee /etc/systemd/system/disable-thp.service << 'EOF'
[Unit]
Description=Disable Transparent Huge Pages
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo never > /sys/kernel/mm/transparent_hugepage/enabled && echo never > /sys/kernel/mm/transparent_hugepage/defrag"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable disable-thp.service

# 4. CPU 性能模式
sudo apt install -y cpufrequtils
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils

# 5. 验证
free -h # 应见 32GB 内存 + 32GB swap
cat /sys/kernel/mm/transparent_hugepage/enabled #应显示[never]
