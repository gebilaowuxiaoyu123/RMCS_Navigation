#!/usr/bin/env bash
# 用【Nav2 默认参数】的新数据重绘 12 张图（2 张地图 × 6 张）
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../.."                       # .. 到 docs/zh-cn/算法组考核
D="${PLANCMP_WORK:-/tmp/plancmp}/${PLANCMP_MAP:-default}"
R="$D/rmuc"
Z="$D/往返"
T=tools/plot_path.py

echo "===== RMUC 汇总 ====="
python3 $T assets/rmuc/path_compare_all.png \
  "NavFn:$R/plan_navfn.txt" \
  "ThetaStar:$R/plan_thetastar.txt" \
  "Smac2D:$R/plan_smac2d.txt" \
  "SmacHybrid:$R/plan_hybrid.txt" \
  "SmacLattice:$R/plan_lattice.txt" \
  --map rmuc --scale 4 --grid 4 --legend-pos br --font-scale 0.55

echo "===== RMUC 单规划器 ====="
i=0
for p in navfn thetastar smac2d hybrid lattice; do
  i=$((i + 1))
  python3 $T assets/rmuc/path_$p.png "$p:$R/plan_$p.txt" \
    --map rmuc --scale 4 --grid 4 --legend-pos br --font-scale 0.55 --color $i
done

echo "===== 战队 汇总（往返，双色）====="
python3 $T assets/zhandui/path_compare_all.png \
  "NavFn:$Z/plan_navfn.txt" \
  "ThetaStar:$Z/plan_thetastar.txt" \
  "Smac2D:$Z/plan_smac2d.txt" \
  "SmacHybrid:$Z/plan_hybrid.txt" \
  "SmacLattice:$Z/plan_lattice.txt" \
  --map 战队 --scale 5 --grid 2 --crop=-3.5,-4.2,7.5,7.2 --legend-pos tl \
  --font-scale 0.42 --two-tone

echo "===== 战队 单规划器（往返，双色）====="
i=0
for p in navfn thetastar smac2d hybrid lattice; do
  i=$((i + 1))
  python3 $T assets/zhandui/path_$p.png "$p:$Z/plan_$p.txt" \
    --map 战队 --scale 5 --grid 2 --crop=-3.5,-4.2,7.5,7.2 --legend-pos tl \
    --font-scale 0.42 --two-tone --color $i
done

echo
echo "===== 产物 ====="
ls -l assets/rmuc assets/zhandui
