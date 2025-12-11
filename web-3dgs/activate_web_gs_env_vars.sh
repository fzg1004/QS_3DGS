#!/bin/bash
# gaussian-splatting环境激活时自动配置的环境变量

export CUDA_HOME="/usr/local/cuda-11.8"
export PATH="$CONDA_PREFIX/bin:$PATH"
export TORCH_CUDA_ARCH_LIST="7.0"
export CC="/usr/bin/gcc"
export CXX="/usr/bin/g++"

# LD_LIBRARY_PATH配置（合并所有路径）
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$CONDA_PREFIX/lib/python3.10/site-packages/torch/lib:/usr/lib/x86_64-gnu:$CONDA_PREFIX/lib:$CONDA_PREFIX/lib64"

# 其他特殊配置
export TORCH_CXX11_ABI="0"
export CFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0 $CFLAGS"
export CXXFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0 $CXXFLAGS"
