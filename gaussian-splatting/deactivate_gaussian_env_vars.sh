#!/bin/bash
# 退出gaussian-splatting环境时清理环境变量
unset CUDA_HOME
unset TORCH_CUDA_ARCH_LIST
# LD_LIBRARY_PATH恢复为原始值（可选，若不想清空则注释）
export LD_LIBRARY_PATH=$(echo $LD_LIBRARY_PATH | sed "s|$CONDA_PREFIX/bin:||g")