"""Visualize PIR array recordings in Dataset/, grouped by scenario (one folder = one scenario).

    python visualize_pir.py list                  # list scenarios and file counts
    python visualize_pir.py plot tb/cot3          # time series of every recording in one scenario
    python visualize_pir.py plot tb               # every scenario of one group
    python visualize_pir.py plot --all            # everything
    python visualize_pir.py heatmap [scope]       # mean |deviation| per sensor vs grid cell
    add --show to open windows instead of only saving PNGs into figures/
"""
import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "Dataset"
FIGURES = ROOT / "figures"

FS = 100                      # Hz, one sample every 10 ms (do an.pdf, muc 2.2.3)
ADC_MAX = 4095                # ESP32 12-bit ADC
IDLE_BAND = (1300, 1600)      # no-motion band used for detection (do an.pdf, hinh 4.6)

# CSV columns b..f. The thesis lists the labels, but the order was recovered from the data:
# the column that is strongest when the person is in the left/right/bottom/top cells.
CHANNELS = [("Left", "tab:blue"), ("Right", "tab:orange"), ("Bottom", "tab:green"),
            ("Top", "tab:red"), ("Center", "tab:purple")]

GROUPS = {
    "tb": "đi dọc cột, từ trên xuống",
    "bt": "đi dọc cột, từ dưới lên",
    "lr": "đi dọc hàng, từ trái sang phải",
    "rl": "đi dọc hàng, từ phải sang trái",
    "cheo": "đi chéo, chiều thứ nhất (tên thư mục: từ ô đầu đến ô cuối)",
    "cheo_2": "đi chéo, chiều ngược lại (cùng tập đường chéo với cheo)",
    "testcase": "quỹ đạo kiểm thử (hình 3.23)",
}


def cell_rc(label):
    """'id73' -> (row, col) on the 6x6 grid of hinh 3.21. Digit 1 = 1 m cell 1..9, digit 2 = sub-cell 1..4."""
    big, sub = int(label[2]) - 1, int(label[3]) - 1
    return big // 3 * 2 + sub // 2, big % 3 * 2 + sub % 2


def is_cell(label):
    return len(label) == 4 and label.startswith("id") and label[2:].isdigit() and label != "id0"


def load(path):
    """Return (t seconds from first sample, x[N,5] ADC counts, ids[N])."""
    ts, xs, ids = [], [], []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if len(row) < 7 or not row[0]:
                continue
            ts.append(float(row[0]))
            xs.append([float(v) for v in row[1:6]])
            ids.append(row[6])
    t = (np.array(ts) - ts[0]) / 1000.0
    if t[-1] <= 0:  # a spreadsheet rounded the timestamps (1.73313E+12): assume uniform sampling
        t = np.arange(len(ts)) / FS
    return t, np.array(xs), ids


def scenarios():
    """All folders under Dataset/ that hold CSVs, as sorted 'group/name' strings."""
    folders = {p.parent for p in DATASET.glob("*/*/*.csv")}
    return sorted(p.relative_to(DATASET).as_posix() for p in folders)


def resolve(scope):
    found = scenarios()
    if scope is None:
        return found
    scope = scope.strip("/\\").replace("\\", "/")
    picked = [s for s in found if s == scope or s.startswith(scope + "/")]
    if not picked:
        raise SystemExit(f"no scenario matches '{scope}'. Run: python visualize_pir.py list")
    return picked


def recordings(scenario, keep_empty=False):
    files = sorted((DATASET / scenario).glob("*.csv"))
    return files if keep_empty else [f for f in files if f.stat().st_size > 0]


def visited_cells(ids):
    """Cells in order of first visit, e.g. ['11', '13', '41']."""
    order = []
    for label in ids:
        if is_cell(label) and (not order or order[-1] != label[2:]):
            order.append(label[2:])
    return order


def describe(scenario):
    group, name = scenario.split("/")
    text = f"{scenario}: {GROUPS.get(group, group)}"
    first = recordings(scenario)[0]
    cells = visited_cells(load(first)[2])
    if cells:
        text += "\nô: " + " → ".join(cells)
    return text


def label_segments(t, ids):
    """Runs of equal id as (t_start, t_end, label)."""
    segs, start = [], 0
    for i in range(1, len(ids) + 1):
        if i == len(ids) or ids[i] != ids[start]:
            segs.append((t[start], t[i - 1], ids[start]))
            start = i
    return segs


def plot_scenario(scenario, ncols=2, ylim=None, show_labels=True):
    import matplotlib.pyplot as plt

    files = recordings(scenario)
    data = [load(f) for f in files]
    ncols = min(ncols, len(files))
    nrows = math.ceil(len(files) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.5 * ncols, 2.6 * nrows + 1.0),
                             sharey=True, squeeze=False)

    if ylim is None:
        lo = min(x.min() for _, x, _ in data)
        hi = max(x.max() for _, x, _ in data)
        ylim = (max(0, math.floor((lo - 100) / 100) * 100), min(ADC_MAX, math.ceil((hi + 100) / 100) * 100))

    for ax, f, (t, x, ids) in zip(axes.flat, files, data):
        for k, (name, color) in enumerate(CHANNELS):
            ax.plot(t, x[:, k], lw=0.9, color=color, label=name)
        ax.axhspan(*IDLE_BAND, color="gray", alpha=0.12, lw=0)
        ax.set_ylim(*ylim)
        if t[-1] > t[0]:  # a few recordings hold a single sample
            ax.set_xlim(t[0], t[-1])
        ax.grid(True, alpha=0.3)
        ax.set_title(f.stem, fontsize=8)
        ax.tick_params(labelsize=7)
        if show_labels:
            segs = [s for s in label_segments(t, ids) if is_cell(s[2])]
            for t0, t1, label in segs:
                ax.axvline(t0, color="k", lw=0.4, ls=":")
                if len(segs) <= 14:
                    ax.text((t0 + t1) / 2, ylim[1], label[2:], ha="center", va="top", fontsize=6)
    for ax in axes.flat[len(files):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("t (s)", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("ADC", fontsize=8)

    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=5, fontsize=8)
    fig.suptitle(f"{describe(scenario)}  ({len(files)} file, {FS} Hz; vùng xám = {IDLE_BAND[0]}-{IDLE_BAND[1]})",
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.8 / fig.get_figheight()))  # leave 0.8 in for the title
    return fig


def plot_heatmap(scenario_list):
    """Mean |ADC - median| per sensor for each labelled grid cell, over all recordings in scope."""
    import matplotlib.pyplot as plt

    total = np.zeros((5, 6, 6))
    count = np.zeros((6, 6))
    for sc in scenario_list:
        for f in recordings(sc):
            _, x, ids = load(f)
            dev = np.abs(x - np.median(x, axis=0))
            for d, label in zip(dev, ids):
                if is_cell(label):
                    r, c = cell_rc(label)
                    total[:, r, c] += d
                    count[r, c] += 1
    mean = np.where(count > 0, total / np.maximum(count, 1), np.nan)

    fig, axes = plt.subplots(1, 5, figsize=(16, 3.8), squeeze=False)
    vmax = np.nanmax(mean)
    for k, ax in enumerate(axes[0]):
        im = ax.imshow(mean[k], cmap="viridis", vmin=0, vmax=vmax)
        ax.set_title(CHANNELS[k][0])
        ax.set_xticks(range(6), [f"c{i + 1}" for i in range(6)], fontsize=7)
        ax.set_yticks(range(6), [f"r{i + 1}" for i in range(6)], fontsize=7)
    fig.colorbar(im, ax=axes[0], shrink=0.8, label="mean |ADC - median|")
    scope = scenario_list[0] if len(scenario_list) == 1 else f"{len(scenario_list)} kịch bản"
    fig.suptitle(f"Biên độ trung bình theo ô và cảm biến ({scope}); hàng 1 = Top, cột 1 = Left", fontsize=10)
    return fig


def finish(fig, out_path, show):
    import matplotlib.pyplot as plt

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=110)
        print("saved", out_path.relative_to(ROOT))
    if not show:
        plt.close(fig)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    parser =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list scenarios")
    for name in ("plot", "heatmap"):
        p = sub.add_parser(name)
        p.add_argument("scope", nargs="?", help="group (tb) or scenario (tb/cot3); omit or --all for everything")
        p.add_argument("--all", action="store_true")
        p.add_argument("--show", action="store_true", help="open windows (default: only save PNGs)")
        p.add_argument("--out", type=Path, default=FIGURES, help="output folder (default: figures/)")
        if name == "plot":
            p.add_argument("--ylim", type=float, nargs=2, metavar=("LO", "HI"), help="default: fit the data")
            p.add_argument("--ncols", type=int, default=2)
            p.add_argument("--no-labels", action="store_true", help="hide the id (grid cell) overlay")
    args = parser.parse_args()

    if args.cmd == "list":
        for sc in scenarios():
            n = len(recordings(sc))
            empty = len(recordings(sc, keep_empty=True)) - n
            note = f"  ({empty} file rỗng bị bỏ qua)" if empty else ""
            print(f"{sc:24s} {n:3d} file   {GROUPS.get(sc.split('/')[0], '')}{note}")
        return

    import matplotlib
    if not args.show:
        matplotlib.use("Agg")

    chosen = resolve(None if args.all else args.scope)
    if args.cmd == "heatmap":
        label = (args.scope or "all").replace("/", "_")
        finish(plot_heatmap(chosen), args.out / f"heatmap_{label}.png", args.show)
    else:
        for sc in chosen:
            fig = plot_scenario(sc, args.ncols, tuple(args.ylim) if args.ylim else None, not args.no_labels)
            finish(fig, args.out / f"{sc}.png", args.show)
    if args.show:
        import matplotlib.pyplot as plt
        plt.show()


if __name__ == "__main__":
    main()
