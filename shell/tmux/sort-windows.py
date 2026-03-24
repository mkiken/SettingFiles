#!/usr/bin/env python3
"""tmux sort-windows: ウィンドウをウィンドウ名でソートする"""
import subprocess


def tmux(*args):
    return subprocess.check_output(["tmux"] + list(args), text=True).strip()


def tmux_run(*args):
    subprocess.run(["tmux"] + list(args), check=True)


lines = tmux("list-windows", "-F", "#{window_index}\t#{window_name}").splitlines()
windows = [(int(idx), name) for idx, name in (line.split("\t", 1) for line in lines)]

sorted_windows = sorted(windows, key=lambda w: w[1].lower())

# selection sort: position i に sorted_windows[i] を移動する
current = list(windows)  # 現在のインデックス順リスト

base_index = current[0][0]  # base-index (通常1)

for i, (_, target_name) in enumerate(sorted_windows):
    current_idx = i + base_index
    # current[i] がターゲットでなければ探してswap
    if current[i][1] != target_name:
        pos = next(j for j in range(i, len(current)) if current[j][1] == target_name)
        swap_idx = pos + base_index
        tmux_run("swap-window", "-s", str(current_idx), "-t", str(swap_idx))
        current[i], current[pos] = current[pos], current[i]

tmux_run("display-message", "Windows sorted!")
