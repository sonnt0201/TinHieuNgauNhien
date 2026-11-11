# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Coursework for EE6423 (random signals / estimation) built around a 5-channel PIR (passive infrared) motion-sensor array. There is no build system, test suite or linter. The pieces are:

- `M0/EE6423_M0_MoTaBaiToan.tex`: the one-page problem statement (milestone M0). It follows Appendix A of `Documents/ee6423_project_brief 1.pdf` and must stay on **one page**. The PDF is committed alongside the source.
- `Documents/EE6423_M1_MiniProposal_D203S.pptx`: the M1 mini-proposal deck, kept consistent with M0 (D203S, fs = 100 Hz, 50 Hz mains at Nyquist). Edit it in place with python-pptx so the HUST template, Quicksand font and red/orange styling stay untouched.
- `Dataset/`: recordings from the sensor array plus throwaway per-folder plotting scripts. It is a **nested git repo** with its own history (remote `Mungnv212894/AI`, the thesis author's repo). Don't `git add` it from the parent. Treat it as read-only input.
- `Documents/`: reference PDFs/slides. `do an.pdf` (Nguyễn Văn Mùng's thesis) is the source for the circuit and the data-collection protocol (chapter 3).
- `visualize_pir.py`: the real analysis/plotting tool (see below). Output goes to `figures/` (git-ignored).

The `M0` text and all folder names are Vietnamese. Keep new prose in Vietnamese to match.

## Commands

```bash
pip install numpy matplotlib                  # only dependencies
python visualize_pir.py list                  # scenarios and file counts
python visualize_pir.py plot tb/cot3          # one scenario -> figures/tb/cot3.png
python visualize_pir.py plot tb               # every scenario in a group
python visualize_pir.py plot --all            # all 73 scenarios (about 2 minutes)
python visualize_pir.py heatmap [scope]       # mean |deviation| per sensor vs grid cell
cd M0 && latexmk -xelatex EE6423_M0_MoTaBaiToan.tex   # needs Times New Roman and TeX Gyre Termes Math
```

Add `--show` to open matplotlib windows instead of only saving PNGs. On Windows, Python's default console encoding breaks Vietnamese output; the script reconfigures stdout itself.

## Hardware (what the data measures)

From `Documents/do an.pdf`, section 3.2. The M0 text is derived from this, so keep the two consistent:

- Sensor D203S (two-element pyroelectric, responds only to changing IR) feeds a two-stage LM358 amplifier/filter. Stage 1 is non-inverting, gain 1+1 MΩ/47 kΩ ≈ 22, band 0.072–15.9 Hz. Stage 2 is inverting, gain −510 kΩ/15 kΩ = −34, band 1.06–31.2 Hz. Total ≈ 748× (57 dB). A 150 kΩ/100 kΩ divider sets the idle level at 0.4·VCC ≈ 1.3 V.
- The final schematic (fig 3.11) and the LTspice figures (3.7, 3.9) label resistors differently, and the thesis text has formula typos. The component values above were checked against the stated cut-off frequencies.
- ESP32 12-bit ADC (GPIO32/33/34/35/39), fs = 100 Hz. At fs = 100 Hz the 50 Hz mains line aliases exactly to Nyquist and its 100 Hz harmonic to DC.
- Array: 1 centre sensor + 4 around it tilted 30°, ceiling height 2.4 m, 3×3 m area.

## Data format

Every `Dataset/**/*.csv` is headerless, 7 columns: epoch ms (10 ms steps), five ADC channels, and an `id` label. File names are `<start_ms> - <end_ms>.csv` (with spaces, so quote paths). The idle level is about 1500 counts, and the thesis treats 1300–1600 as "no motion".

- **Channel order (recovered from the data, not from the thesis):** columns 2–6 are Left, Right, Bottom, Top, Center. The thesis lists labels in a different order. `visualize_pir.py` heatmaps confirm this: each channel peaks in its own half of the grid.
- **`id` is the ground-truth position:** `id0` means the person is outside the area, and `idXY` is a grid cell. The 6×6 grid of fig 3.21 is numbered `X` = 1 m cell 1–9 (row-major in a 3×3 layout) and `Y` = 0.5 m sub-cell 1–4 (TL, TR, BL, BR). The script's `cell_rc()` converts a label to (row, col).
- One file, `Dataset/cheo_2/tu_73_32/1733125367183 - 1733125377793.csv`, is empty and is skipped. About 60 others have one malformed or truncated row, which the loader skips. `cheo_2/tu_73_32/1733125666123 - 1733125677370.csv` has its timestamps rounded to `1.73313E+12` (saved through a spreadsheet), so the loader assumes uniform 100 Hz spacing for it.

## Scenario layout

Each folder is one scenario (about 10 recordings of a person walking a path):

| Group | Subfolders | Path |
|---|---|---|
| `tb` / `bt` | `cot1`..`cot6` (+ `tb/cot1_2`) | down / up one grid column |
| `lr` / `rl` | `hang1`..`hang6` | left→right / right→left along one grid row |
| `cheo` / `cheo_2` | `tu_XY_ZW` | diagonals between cells XY and ZW; `cheo_2` is the same diagonals in the opposite direction |
| `testcase` | `test1`..`test4` | the zig-zag test trajectories of fig 3.23 |

`Dataset/*/*/main.py` and `main10.py` are older per-folder copies of the plotting code with hard-coded file names (about 50 are identical apart from the names), and `tempCodeRunnerFile.py` files are VS Code Code Runner leftovers. Prefer `visualize_pir.py`; don't extend the per-folder scripts.
