#!/bin/bash
# hw_verify.sh

echo "====== HeteroService 硬件验证 ======"

echo "[1/8] CPU 信息"
LC_ALL=C lscpu | grep -E "Model name|Core|Thread|MHz" | head -10

echo "[2/8] 内存配置"
sudo dmidecode -t memory | grep -E "Size|Speed|Configured" | head -20

echo "[3/8] GPU 列表"
nvidia-smi --query-gpu=name,memory.total,driver_version --format csv

echo "[4/8] PCIe 拓扑"
nvidia-smi topo -m

echo "[5/8] PCIe 链路速度"
sudo lspci -vv | grep -E "VGA|3D|LnkSta" | grep -A1 "VGA\|3D"

echo "[6/8] 系统盘类型"
lsblk -d -o NAME,ROTA,TRAN,SIZE,MODEL
echo "[7/8] NVME 速度"
sudo nvme list 2>/dev/null
sudo lspci -vv | grep -A 30 "non-volatile" | grep -E "LnkSta|LnkCap" | head -5

echo "[8/8] 内存与swap状态"
free -h
cat /proc/swaps

echo "验证完成"
