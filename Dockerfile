# 将 CUDA, Pytorch, vllm, Flashinfer 这些核心推理依赖作为一个整体固定

# 只有在新版本通过 bake-off 后才修改这个参数
# ARG 指令定义是在构建期使用的参数。构建完成后,运行期就不能使用了。ENV是构建期和运行期都可以使用的环境变量
ARG VLLM_VERSION=v0.21.0 

# 基础镜像和版本
FROM m.daocloud.io/docker.io/vllm/vllm-openai:${VLLM_VERSION}

# LABEL 说明
LABEL org.opencontainers.image.title="HeteroServe vLLM OpenAI server" \
      org.opencontainers.image.description="Qwen3 inference on Turing/SM75 GPUs"

ENV CUDA_DEVICE_ORDER=PCI_BUS_ID PYTHONUNBUFFERED=1

WORKDIR /app

# 下面不重装任何核心包，只在构建期确认官方镜像包含 vllm 和 Flashinfer. 检查不导入 CUDA 模块，构建机无需GPU
RUN python3 -c "import importlib.util; assert importlib.util.find_spec('vllm'); assert importlib.util.find_spec('flashinfer')"

EXPOSE 8000
STOPSIGNAL SIGTERM