#!/bin/bash
# 退出gaussian-splatting环境时清理环境变量
unset CUDA_HOME
unset TORCH_CUDA_ARCH_LIST
unset TORCH_CXX11_ABI
unset CFLAGS
unset CXXFLAGS