#!/bin/bash
# gaussian-splatting环境激活时自动配置的环境变量

# 基础CUDA/编译器配置
export CUDA_HOME="$CONDA_PREFIX"
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_CUDA_ARCH_LIST="7.0"
export CC="$CONDA_PREFIX/bin/gcc"
export CXX="$CONDA_PREFIX/bin/g++"

# LD_LIBRARY_PATH配置（合并所有路径）
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib/python3.8/site-packages/torch/lib:/usr/lib/x86_64-linux-gnu:$CUDA_HOME/lib:$CUDA_HOME/lib64"
