#!/usr/bin/env python3
"""在「战队」地图上依次跑 5 个全局规划器，把每次 /compute_path_to_pose 的输出存下来。

思路：static.launch.yaml 的 configuration 参数可覆盖 ⇒ 每个规划器一份独立配置目录，
      不动仓库里的 config/motion.yaml。
"""
import argparse
import math
import os
import re
import shutil
import signal
import subprocess
import time

SRC = os.environ.get("RMCS_NAV_SRC",
                     "/workspaces/RMCS/rmcs_ws/src/rmcs-navigation-deps/rmcs-navigation")
WORK = os.environ.get("PLANCMP_WORK", "/tmp/plancmp")   # 输出根目录（换机器可改）
LATTICE = f"{SRC}/lattice/omni_10cm.json"
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # …/算法组考核/tools

_ap = argparse.ArgumentParser(description="在指定地图上依次跑 5 个全局规划器")
_ap.add_argument("--map", default="战队", help="maps/<名>.yaml 里的地图名")
_ap.add_argument("--start", default="8.30,6.90", help="起点 world x,y")
_ap.add_argument("--goal", default="9.60,-2.90", help="终点 world x,y")
_ap.add_argument("--only", default="", help="只跑某个规划器（调试用），如 hybrid")
_ap.add_argument("--out", default="", help="输出目录（默认 /tmp/plancmp/<map>）")
_ap.add_argument("--probe", default="", help="启动后顺带读这些世界坐标的代价，如 '0.65,-0.45;0.65,-0.4'")
_ap.add_argument("--start-yaw", type=float, default=None,
                 help="起点朝向（度，0=+x）。不给则按 start→goal 方向自动算")
_ap.add_argument("--goal-yaw", type=float, default=None,
                 help="终点朝向（度）。不给则与起点相同")
_a = _ap.parse_args()

MAP = _a.map
START = tuple(float(v) for v in _a.start.split(","))
GOAL = tuple(float(v) for v in _a.goal.split(","))
OUT = _a.out or f"{WORK}/{MAP}"   # 每张地图一个输出目录，两张图结果互不覆盖

# Dubins(Hybrid) 是前向-only，起点朝向给错就必然 "no valid path found" ⇒ 默认沿行进方向
if _a.start_yaw is None:
    START_YAW = math.degrees(math.atan2(GOAL[1] - START[1], GOAL[0] - START[0]))
else:
    START_YAW = _a.start_yaw
GOAL_YAW = _a.goal_yaw if _a.goal_yaw is not None else START_YAW


def quat(deg):
    """yaw(度) -> (z, w)"""
    h = math.radians(deg) / 2.0
    return math.sin(h), math.cos(h)


STRAY = ("ros2 launch rmcs-navigation", "planner_server", "controller_server",
         "bt_navigator", "behavior_server", "smoother_server", "waypoint_follower",
         "map_server", "costmap", "lifecycle_manager", "foxglove_bridge",
         "static_transform_publisher")


def _n_servers(env):
    """当前 /compute_path_to_pose 的 action 服务器个数（-1 = 查不到）"""
    info = subprocess.run(["ros2", "action", "info", "/compute_path_to_pose"],
                          capture_output=True, text=True, env=env, timeout=20).stdout
    m = re.search(r"Action servers:\s*(\d+)", info)
    return int(m.group(1)) if m else -1


def clean_strays():
    """⚠️ 残留的 nav2 进程会【抢答】同一个 action ⇒ 拿到假结果（已踩过）。
    光杀进程不够：ros2 daemon 会【缓存已死的节点】，所以还要停 daemon 并等真的没服务器。"""
    env = dict(os.environ, ROS_DOMAIN_ID="42")
    for pat in STRAY:
        subprocess.run(["pkill", "-9", "-f", pat], capture_output=True)
    subprocess.run(["ros2", "daemon", "stop"], capture_output=True, env=env)
    for _ in range(15):
        time.sleep(1)
        if _n_servers(env) <= 0:
            return
    print("  ⚠️ 清理后仍有 /compute_path_to_pose 服务器残留", flush=True)


def repo_gridbased_block():
    """从仓库 config/motion.yaml 里抽出【真车当前值】的 GridBased 块（只读，不修改仓库）。"""
    lines = open(f"{SRC}/config/motion.yaml", encoding="utf-8").read().split("\n")
    s = next(i for i, l in enumerate(lines) if l.strip().startswith("GridBased:"))
    e = next(i for i in range(s + 1, len(lines)) if lines[i] and not lines[i][0].isspace())
    blk = lines[s + 1:e]
    # 车上的 lattice_filepath 指向 /rmcs_install/...，本地跑要换成本工作区的原语文件
    blk = [f'      lattice_filepath: "{LATTICE}"' if l.strip().startswith("lattice_filepath") else l
           for l in blk]
    return "\n".join(blk)

PLANNERS = {
    # ★ 纯默认（含 use_astar: true）—— 实测本图 3/3 可用
    "navfn": '      plugin: "nav2_navfn_planner::NavfnPlanner"',
    # 取证用：NavFn 纯默认（use_astar: true），只在 --only navfn_astar 时跑
    "navfn_astar": '      plugin: "nav2_navfn_planner::NavfnPlanner"',
    "thetastar": '      plugin: "nav2_theta_star_planner::ThetaStarPlanner"',
    "smac2d": '      plugin: "nav2_smac_planner::SmacPlanner2D"',
    "hybrid": '      plugin: "nav2_smac_planner::SmacPlannerHybrid"',   # motion_model 默认 DUBIN
    # lattice 必须给原语文件（没有默认值），其余全部默认
    # ⚠️ 唯一一处非默认：change_penalty 0.05 → 1.0
    #    默认 0.05 时本规划器会给出【穿墙】路径（地图逐格比对 + 未平滑原始路径双重确认）；
    #    提到 1.0 后路径合法。详见 docs 里的参数说明。
    "lattice": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
               '      lattice_filepath: "%s"\n      change_penalty: 1.0' % LATTICE,
    # 对照用：Lattice 纯默认（会穿墙，用于取证）
    "lattice_pure": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
                    '      lattice_filepath: "%s"' % LATTICE,
    # 对照用：仓库里【真车调好的那套】（只读抽取，不修改仓库文件）
    # 与上面的默认态跑同一段路 → 用来说明「默认 vs 调参」差多少
    "lattice_repo": repo_gridbased_block(),
    # 诊断用：只把默认平滑器关掉（其余全默认）
    "lattice_nosmooth": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
                        '      lattice_filepath: "%s"\n      smooth_path: false' % LATTICE,
    # 诊断用：只抬 non_straight_penalty（其余全默认）
    "lattice_nsp": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
                   '      lattice_filepath: "%s"\n      non_straight_penalty: 2.4' % LATTICE,
    # ── 下面四个：逐个试「仓库与默认不一样的参数」，看哪个能消除穿墙 ====
    "d_override": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
                  '      lattice_filepath: "%s"\n      analytic_expansion_max_cost_override: false' % LATTICE,
    "d_change": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
                '      lattice_filepath: "%s"\n      change_penalty: 1.0' % LATTICE,
    "d_retro": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
               '      lattice_filepath: "%s"\n      retrospective_penalty: 0.04\n      reverse_penalty: 20.0' % LATTICE,
    "d_time": '      plugin: "nav2_smac_planner::SmacPlannerLattice"\n'
              '      lattice_filepath: "%s"\n      max_planning_time: 10.0\n      max_on_approach_iterations: 300' % LATTICE,
}
ORDER = ["navfn", "thetastar", "smac2d", "hybrid", "lattice"]


def make_motion_yaml(block, dst_dir):
    lines = open(f"{SRC}/config/motion.yaml", encoding="utf-8").read().split("\n")
    start = next(i for i, l in enumerate(lines) if l.strip().startswith("GridBased:"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] and not lines[i][0].isspace())
    # ⚠ 必须保留 lines[start] 这一行（即 `    GridBased:`），否则键就丢了
    new = lines[:start + 1] + block.split("\n") + [""] + lines[end:]
    os.makedirs(dst_dir, exist_ok=True)
    text = "\n".join(new)
    # 自检：能解析、且 GridBased 下确实有 plugin
    import yaml
    parsed = yaml.safe_load(text)
    gb = parsed["planner_server"]["ros__parameters"]["GridBased"]
    assert "plugin" in gb, f"GridBased 下没有 plugin: {gb}"
    open(f"{dst_dir}/motion.yaml", "w", encoding="utf-8").write(text)
    shutil.copy(f"{SRC}/config/motion.xml", f"{dst_dir}/motion.xml")
    return gb["plugin"]


def lifecycle_state(node, env):
    try:
        out = subprocess.run(
            ["ros2", "lifecycle", "get", node], capture_output=True, text=True,
            timeout=8, env=env,
        ).stdout
        return out.strip()
    except Exception:
        return "?"


def run_one(name):
    cfg = f"{OUT}/{name}"
    out_txt = f"{OUT}/plan_{name}.txt"
    log = f"{OUT}/log_{name}.txt"
    plugin = make_motion_yaml(PLANNERS[name], cfg)
    print(f"  [{name}] plugin = {plugin}")

    env = dict(os.environ, ROS_DOMAIN_ID="42")
    with open(log, "w") as lf:
        proc = subprocess.Popen(
            ["ros2", "launch", "rmcs-navigation", "static.launch.yaml",
             f"global_map:={MAP}", f"configuration:={cfg}"],
            stdout=lf, stderr=subprocess.STDOUT, env=env,
            preexec_fn=os.setsid,
        )

    state = "?"
    for _ in range(40):
        time.sleep(2)
        state = lifecycle_state("/planner_server", env)
        if "active" in state:
            break
    if "active" not in state:
        print(f"  [{name}] ❌ planner_server 未激活（{state}）")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        return False

    # 顺手把 planner_server 的【生效参数全量】dump 下来，作为「全默认」的证据
    try:
        dump = subprocess.run(["ros2", "param", "dump", "/planner_server"],
                              capture_output=True, text=True, env=env, timeout=20).stdout
        open(f"{OUT}/params_{name}.yaml", "w", encoding="utf-8").write(dump)
    except Exception as e:
        print(f"  [{name}] 参数 dump 失败: {e}")

    # ⚠ 核对：只允许 1 个 /compute_path_to_pose 服务器，否则结果可能是别人回的
    n_srv = -1
    for _ in range(12):
        n_srv = _n_servers(env)
        if n_srv == 1:
            break
        time.sleep(2)
    if n_srv != 1:
        print(f"  [{name}] ❌ 检测到 {n_srv} 个 /compute_path_to_pose 服务器，结果不可信！")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        return False

    if _a.probe:
        print(f"  [{name}] 代价图探针:")
        subprocess.run(["python3", os.path.join(TOOLS, "costmap_probe.py"),
                        "--points", _a.probe], env=env)

    _sz, _sw = quat(START_YAW)
    _gz, _gw = quat(GOAL_YAW)
    goal = (
        "{start: {header: {frame_id: world}, pose: {position: {x: %.3f, y: %.3f, z: 0.0}, "
        "orientation: {z: %.8f, w: %.8f}}}, goal: {header: {frame_id: world}, pose: {position: "
        "{x: %.3f, y: %.3f, z: 0.0}, orientation: {z: %.8f, w: %.8f}}}, use_start: true}"
        % (START[0], START[1], _sz, _sw, GOAL[0], GOAL[1], _gz, _gw)
    )
    try:
        res = subprocess.run(
            ["ros2", "action", "send_goal", "/compute_path_to_pose",
             "nav2_msgs/action/ComputePathToPose", goal],
            capture_output=True, text=True, env=env, timeout=120,
        )
        open(out_txt, "w", encoding="utf-8").write(res.stdout + res.stderr)
        n = len(re.findall(r"position:", res.stdout))
        ok = "error_code: 0" in res.stdout and n > 1
        print(f"  [{name}] {'✅' if ok else '❌'} {'成功' if ok else '失败'}，{n - 1} 个位姿点 -> {out_txt}")
    except subprocess.TimeoutExpired:
        print(f"  [{name}] ❌ 超时")
        ok = False

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass
    time.sleep(3)
    return ok


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if not os.environ.get("NO_CLEAN"):
        clean_strays()
    print(f"地图={MAP}  起点={START} 朝向{START_YAW:.1f}°  终点={GOAL} 朝向{GOAL_YAW:.1f}°  输出={OUT}\n")
    todo = [_a.only] if _a.only else ORDER
    for name in todo:
        print(f"=== {name} ===")
        clean_strays()          # ⚠️ 每次都清，残留会抢答（见 clean_strays 注释）
        run_one(name)
        print()
    print("完成。")
