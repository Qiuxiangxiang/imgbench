#!/bin/bash
# JPEG AI 参考软件 · Apple Silicon 熵编码扩展构建脚本
# 用法：克隆官方仓库后，在其根目录执行  bash patches/build_ec_mac.sh
# 依赖：brew install libomp；venv 中 pip install pybind11
set -e
PY=${PYTHON:-python3}
INC=$($PY -m pybind11 --includes)
SUF=$($PY -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))")
OMP=$(brew --prefix libomp)

# 注意：zsh 默认不做单词分割，bash 下直接 $INC 即可
for mod in mans direct; do
  cd src/codec/entropy_coding/cpp_exts/$mod
  if [ "$mod" = mans ]; then SRCS="ans.cpp compressor.cpp decompressor.cpp"; OUT="ans$SUF"; DST=../../lib_wrappers/mans/
  else SRCS="ec_lib_direct.cpp py_ec_lib_direct.cpp"; OUT="ec_direct$SUF"; DST=../../lib_wrappers/direct/; fi
  clang++ -O3 -std=c++14 -shared -fPIC -undefined dynamic_lookup \
    -Xpreprocessor -fopenmp -I$OMP/include -L$OMP/lib -lomp \
    $INC $SRCS -o $OUT
  mv $OUT $DST
  cd - > /dev/null
  echo "built: $OUT → $DST"
done
echo "== 两个熵编码扩展构建完成 =="
