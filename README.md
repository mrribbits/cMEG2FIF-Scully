# cMEG2fif

Convert Cerca Magnetics / QuSpin OPM-MEG recordings (`.cMEG`) to MNE-Python FIF files, with sensor geometry, head coregistration, decoded trigger and button channels, and a provenance log for every conversion.

Based on the original `cMEG2fif` script by Molly Rea (v2.1, 2023).

## What it does

- **Reads the original recording.** It finds every numbered part (`_meg_001.cMEG`, `_meg_002.cMEG`, …) and joins them into one recording. It checks for missing parts and time gaps between parts.
- **Sets up the sensors.** Every sensor axis (X/Y/Z) becomes an MNE magnetometer, placed and oriented from the helmet configuration and converted from volts to tesla using each channel's gain. Sensors without a helmet slot become reference channels.
- **Adds head coregistration.** When digitisation is given, it stores the head shape, fiducials and the device-to-head transform, then shows a 3D alignment check.
- **Decodes triggers.** The eight VPixx Pixel Mode trigger lines are combined into one `STI101` channel, so `mne.find_events(raw)` returns your condition codes directly.
- **Decodes button presses.** Button boxes and other BNC peripherals are named and typed from a simple TSV file. Buttons are combined into one `STI_BTN` channel whose event codes identify the button.
- **Records the conversion.** Everything shown on screen is saved to a log with a provenance header: script version, command line, host, and package versions.
- **Protects your data.** It never overwrites existing output unless you pass `--force`.

## Repository contents

| File | Purpose |
|---|---|
| `cMEG2fif.py` | The converter. Full documentation is also at the top of the script. Check the version with `python cMEG2fif.py --version`. |
| `cMEG_peripherals.tsv` | Defines what is plugged into each BNC input (buttons, eye tracker, …). |
| `pyproject.toml` | Lets the converter be installed with `pip` (see below). |

## Installation

There are two ways to use the converter.

### Option 1: install with pip (recommended for pipelines)

Install it into your Python or conda environment straight from GitHub:

```
pip install "git+https://github.com/mrribbits/cMEG2FIF-Scully.git"
```

This installs `numpy`, `pandas`, `mne` and `tzdata` if they're missing, and adds a `cmeg2fif` command that takes the same options as `python cMEG2fif.py`:

```
cmeg2fif --version
cmeg2fif 20260924_103257_meg_001.cMEG --no-plot
```

To also install the packages for the 3D alignment plot, add `[plot]`:

```
pip install "cmeg2fif[plot] @ git+https://github.com/mrribbits/cMEG2FIF-Scully.git"
```

For reproducible installs (for example in a shared pipeline), install a fixed version by adding a commit ID or tag after `@`:

```
pip install "git+https://github.com/mrribbits/cMEG2FIF-Scully.git@<commit-or-tag>"
```

The install also includes a copy of `cMEG_peripherals.tsv`, used when `--peripherals` isn't given and the data folder has none. To use a different map, pass `--peripherals`.

### Option 2: run the script directly

Download `cMEG2fif.py` (and `cMEG_peripherals.tsv`) and run it with Python. Install the requirements first:

```
pip install numpy pandas mne tzdata pyvista pyvistaqt pyqt6
```

- **For conversion:** `numpy`, `pandas` and `mne` (mne brings `scipy` and `matplotlib`), plus `tzdata` for the time-zone database used to set the recording date (built into macOS and Linux, needed on Windows).
- **For the 3D plot only:** `pyvista`, `pyvistaqt` and a Qt binding (`pyqt6`, `pyqt5` or `pyside6`). The plot appears when `--dig` is used. Without these packages, add `--no-plot`.
- **With conda:** `conda install -c conda-forge mne` installs everything, including the plotting packages.

## Input files

Cerca's acquisition software writes these next to each other, sharing a prefix such as `20260924_113141`:

| File | Contents |
|---|---|
| `<prefix>_meg_001.cMEG` (`_002`, …) | Raw data. Pass any part to the script. |
| `<prefix>_meg.json` | Sampling rate, duration, recording comment |
| `<prefix>_channels.tsv` | Channel names, types, gains (V/nT), good/bad status |
| `<prefix>_HelmConfig.tsv` | Sensor positions and orientations in the helmet |
| `<prefix>_SessionInfo.txt` | Recording start time (UTC), operator, OPM gain and session notes. Optional, but it's the preferred source for the recording date ([what's used](#sessioninfotxt)). Use `--session-info` if it has a different name or location. |

For subject recordings with head coregistration you also need these files:

| File | Passed as |
|---|---|
| Device-to-head transform, e.g. `subject003_headHelmet_dev2head_xfm.tsv` | `--xfm` |
| Head-shape points, e.g. `subject003_headHelmet_digitisation_from_mesh_3_xfmd.xyz` (last three rows: nasion, LPA, RPA) | `--dig` |

The unnumbered `<prefix>_meg.cMEG` is never used, because it may be an edited copy rather than the original.

## Usage

Examples are for macOS/Linux. In the Windows command prompt, end continued lines with `^` instead of `\`.

`<prefix>_SessionInfo.txt` is picked up automatically from the data folder, so `--session-info` is only needed when that file has a different name or location.

```bash
# Empty-room recording (no coregistration)
python cMEG2fif.py 20260924_103257_meg_001.cMEG

# Subject recording with head coregistration
# (20260924_113141_SessionInfo.txt in the same folder is used automatically)
python cMEG2fif.py 20260924_113141_meg_001.cMEG \
    --xfm subject003_headHelmet_dev2head_xfm.tsv \
    --dig subject003_headHelmet_digitisation_from_mesh_3_xfmd.xyz

# SessionInfo.txt kept in another folder or renamed
python cMEG2fif.py 20260924_113141_meg_001.cMEG \
    --session-info ../session_notes/20260924_113141_SessionInfo.txt \
    --xfm subject003_headHelmet_dev2head_xfm.tsv \
    --dig subject003_headHelmet_digitisation_from_mesh_3_xfmd.xyz

# Re-convert, replacing earlier output, without the 3D plot
python cMEG2fif.py 20260924_113141_meg_001.cMEG \
    --xfm subject003_headHelmet_dev2head_xfm.tsv \
    --dig subject003_headHelmet_digitisation_from_mesh_3_xfmd.xyz \
    --force --no-plot
```

Run `python cMEG2fif.py -h` for the option list, or `python cMEG2fif.py --version` for the script version.

### Options

| Option | Default | Description |
|---|---|---|
| `CMEG_FILE` | *required* | Any part of the recording (`<prefix>_meg_NNN.cMEG`) |
| `--xfm FILE` | `<prefix>_SensorTransform.tsv` | 4×4 device→digitisation transform; used only with `--dig`. Omit for empty room. |
| `--dig FILE` | `<prefix>_digitisation.xyz` | Head-shape points; last 3 rows NAS, LPA, RPA. Omit for empty room. |
| `--session-info FILE` | `<prefix>_SessionInfo.txt` | Cerca session file: recording start time (UTC), operator, comments, OPM gain and session checks ([details](#sessioninfotxt)). Optional; without it, the file name gives the recording date. |
| `--peripherals FILE` | `cMEG_peripherals.tsv` in the data folder, else next to the script, else the copy installed with pip | BNC peripherals definition |
| `--out FILE` | `<prefix>_meg.fif` | Output FIF; the log is written next to it |
| `--force` | off | Overwrite an existing FIF, its split parts and its log |
| `--double` | off (float32) | Store data as float64. Doubles file size; float32 rounding (~6×10⁻⁸ of each value) is far below OPM sensor noise, so use this only for bit-exact archiving or pipeline comparisons ([details](#how-the-meg-values-are-stored)). |
| `--line-freq HZ` | `60` | Mains frequency (the JSON value is ignored; Cerca writes 0) |
| `--timezone TZ` | `America/New_York` | Time zone of the acquisition PC clock, used to convert the file-name timestamp to UTC. That becomes the recording date only when `SessionInfo.txt` has none; otherwise it's a cross-check ([details](#recording-date)). |
| `--min-samples N` | `3` | Shortest code kept in `STI101`/`STI_BTN`, in samples |
| `--max-hsp N` | `0` (all) | Keep a random subset of at most N head-shape points. Uses a fixed seed (same points every run) and always keeps the fiducials. Useful for dense mesh-derived head shapes (~50k points), which slow plotting and MRI coregistration. |
| `--no-plot` | off | Skip the 3D sensor/head alignment plot |
| `--version` | | Show the script version and exit |

## Output

- **`<prefix>_meg.fif`**: the converted recording. Recordings over 2 GB are split by MNE into `<prefix>_meg.fif`, `<prefix>_meg-1.fif`, …; open the first file and the rest load automatically.
- **`<prefix>_meg_conversion_log.txt`**: everything printed during conversion, beginning with a provenance header like this:

  ```
  cMEG2fif version 2.15
    Run:      2026-09-28 16:23:13 EDT
    Command:  cMEG2fif.py 20260924_113141_meg_001.cMEG --xfm ... --dig ...
    Script:   C:\...\cMEG2fif.py
    Host:     <computer> (Windows-...)
    Versions: Python 3.x, MNE 1.x, NumPy 2.x, pandas 2.x
    Output:   single precision (float32, default)
  ```

  The log also records the input parts, the `SessionInfo.txt` fields, the recording start time from each source, the recording type, the peripherals file used, detected trigger and button levels, the channel summary, the recording comment, bad channels and the files written.

### Recording date

Cerca doesn't store the date inside the `.cMEG` data. The converter takes the recording start time from two places, in this order:

1. **`<prefix>_SessionInfo.txt`** (preferred). Its first line gives the start time, already in UTC:

   ```
   MEG Data, recording started 29/09/2026 - 17:40:22
   ```

   The date is **day/month/year**. It's parsed explicitly in that order, so an early-month date like `03/10/2026` is always 3 October, never 10 March.

2. **The file-name prefix** (fallback). It's the start time in local time on the acquisition PC, converted to UTC with `--timezone`. Daylight saving is handled: a September recording in `America/New_York` is UTC−4, a January one UTC−5.

   ```
   20260929_134022_meg_001.cMEG   ->   2026-09-29 13:40:22 EDT = 17:40:22 UTC
   ```

The result is stored as the FIF's recording date (`meas_date`). When both sources are available, the converter compares them and logs both:

```
Recording start (from SessionInfo, UTC): 2026-09-29 17:40:22 UTC
Recording start (from the file name, America/New_York): 2026-09-29 13:40:22 EDT = 2026-09-29 17:40:22 UTC
  File name and SessionInfo agree.
```

If they differ by more than 5 seconds, a warning is logged and the `SessionInfo.txt` time is used:

- **A whole number of hours apart:** usually `--timezone` doesn't match the acquisition PC's time zone, or the PC's time zone or daylight-saving setting is wrong.
- **Any other difference:** usually the file was renamed (the prefix is no longer the original timestamp), or the PC clock was changed.

Other details:

- **Why it matters:** MNE and MNE-BIDS use `meas_date` for the `acq_time` column in `scans.tsv`, for date-shifting when anonymising, and for matching empty-room recordings by date. Without it, those are blank or fail.
- **Renamed files:** a renamed file still gets the correct date from `SessionInfo.txt`, as long as it was renamed together with the recording (same prefix). The log notes that the file name couldn't be used as a cross-check.
- **Missing or unreadable `SessionInfo.txt`:** the file-name time is used. If that isn't a `YYYYMMDD_HHMMSS` timestamp either, the FIF is saved without a recording date, with a warning.
- **Other sites:** set `--timezone` to the time zone the acquisition PC's clock is set to, as an IANA name (e.g. `Europe/London`, `America/Chicago`). The default is the Scully Center's `America/New_York`.
- **Clock accuracy:** both sources come from the acquisition PC's clock, so the date is only as correct as that clock. Keep it synchronised to network time.
- **Converting on another computer:** the result doesn't depend on the converting computer's own clock or time zone (a cluster set to UTC gives the same answer).

### SessionInfo.txt

Cerca writes `<prefix>_SessionInfo.txt` alongside each recording. The converter finds it automatically; use `--session-info FILE` if it has been renamed or stored elsewhere.

```
MEG Data, recording started 29/09/2026 - 17:40:22
Operator: Pinsk
Patient ID: 001
Ethics Code: 16967
Experiment Type: Measurement
Room Degaussed: Yes
Helmet: See TSV
OPM V/nT: 2.70
Comments:
```

Every field is written to the conversion log. The converter also uses them as follows:

| Field | Use |
|---|---|
| `recording started` | Recording date (`meas_date`); see [Recording date](#recording-date) |
| `Operator` | Stored as `raw.info['experimenter']` |
| `Comments` | Appended to `raw.info['description']` |
| `OPM V/nT` | Checked against the gains in `channels.tsv`, with a warning if they differ by more than 1% (the `channels.tsv` values are used) |
| `Room Degaussed` | A warning if it says `No` |
| `Experiment Type` | Checked against the JSON `RecordingType` and against how the file is being converted (see below) |
| `Patient ID`, `Ethics Code` | Logged only; never written into the FIF |

**Recording-type check.** `Experiment Type` (SessionInfo) and `RecordingType` (JSON) say whether the run is an empty-room recording (`Noise`) or a subject recording (`Measurement`). The converter warns when:

- the two disagree;
- an empty-room recording is given `--xfm`/`--dig` (empty-room FIFs normally have no head coregistration);
- a subject recording has no `--dig` (the FIF would have no head coregistration).

These are warnings only; the conversion still runs, since there can be good reasons for either.

**Anonymising.** `raw.anonymize()` (and MNE-BIDS anonymisation) replaces `experimenter` and `description` as well as shifting the date. Operator names and free-text comments therefore don't leak into shared data.

### Channels in the FIF

| Type | Channels |
|---|---|
| `mag` | Every on-head OPM sensor axis, with position and orientation |
| `ref_meg` | Sensors listed in `channels.tsv` with no helmet slot (e.g. off-head references) |
| `stim` | The 8 VPixx trigger lines, **`STI101`**, button channels and **`STI_BTN`** |
| `misc` | Analog BNC peripherals (e.g. eye tracker) and any undefined BNC input, stored in volts as recorded |

Other details:
- **Bad channels:** channels marked `bad` in `channels.tsv` are carried into `raw.info['bads']`.
- **Recording comment:** the JSON `TaskDescription`, plus any `Comments:` from `SessionInfo.txt`, is copied into `raw.info['description']` (joined with ` | `), so the notes travel with the FIF. The source files are never changed.
- **Operator:** the `SessionInfo.txt` operator is stored as `raw.info['experimenter']`.
- **Line frequency:** `raw.info['line_freq']` is set to 60 Hz.

A typical run summarises the channels like this:

```
192 MEG channels, 6 reference channels, 20 stim channels (incl. 8 VPixx trigger
channels, STI101, 10 BNC button channels, and STI_BTN), 6 misc channels (incl.
eye_x, eye_y, and eye_pupil)
```

## Triggers, buttons and peripherals

### VPixx triggers → `STI101`

Trigger lines 1–8 carry the bits of the VPixx Pixel Mode code. They are kept as individual stim channels and also combined into `STI101`:

| Line | Trigger 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Value | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 |

`STI101` is MNE's default stim channel name, so `mne.find_events(raw)` uses it without further arguments.

### BNC peripherals: `cMEG_peripherals.tsv`

Define every BNC input in use. Tab-separated, with a header row:

```
channel	type	name
BNC 1	button	R_thumb
BNC 2	button	R_index
...
BNC 11	misc	eye_x
```

| `type` | Result |
|---|---|
| `button` | Stim channel, **and** a bit in `STI_BTN`. The first button listed = 1, then 2, 4, 8, … |
| `stim` | Stim channel only |
| `misc` | Analog channel, voltage kept as recorded |
| `drop` | Removed from the output |

- **Renaming:** `name` renames the channel, so analysis code can refer to `R_thumb` rather than `BNC 1`.
- **Undefined inputs:** BNC inputs not in the file are kept as `misc` under their original names.
- **Checking:** each run lists every BNC channel and whether its role came from the peripherals file or the default.

The facility file defines these inputs:

| BNC | Name | Type | `STI_BTN` value |
|---|---|---|---|
| 1–5 | `R_thumb`, `R_index`, `R_middle`, `R_ring`, `R_pinky` | button | 1, 2, 4, 8, 16 |
| 6–10 | `L_thumb`, `L_index`, `L_middle`, `L_ring`, `L_pinky` | button | 32, 64, 128, 256, 512 |
| 11–13 | `eye_x`, `eye_y`, `eye_pupil` | misc | none |
| 14–16 | *(undefined)* | misc | none |

To use a different setup for one study, copy the file, edit it, and pass it with `--peripherals`.

### How lines are decoded

Trigger and button voltages are not recorded in the Cerca metadata, so each line is decoded as follows:

- **Resting level:** the line's median.
- **Polarity:** active-high or active-low, taken from the direction of its largest deviation.
- **Threshold:** half of that swing.
- **Unused lines:** a line whose swing is under 0.5 V is treated as unused.
- **Transitions:** changes shorter than `--min-samples` (default 3 samples, 2.5 ms at 1200 Hz) are merged into the neighbouring value. This absorbs one line switching a sample before the others; VPixx codes last at least one video frame, so real codes are unaffected.

The detected levels are printed and logged for every line, for example:

```
bit    1  Trigger 1 [Z]: rest 0.00 V, active-high to 5.02 V
bit    1  R_thumb (BNC 1 [Z]): rest 3.30 V, active-low to -0.03 V
```

## Finding events in MNE

```python
import numpy as np
import mne

raw = mne.io.read_raw_fif('20260924_113141_meg.fif')

# VPixx stimulus codes (STI101 is the default stim channel)
events = mne.find_events(raw)

# If a code can change directly to another without returning to 0
# (e.g. 5 -> 3), add consecutive=True or the second code is missed
events = mne.find_events(raw, consecutive=True)

# Button presses: the event code says which button
buttons = mne.find_events(raw, stim_channel='STI_BTN')
button_id = {'R_thumb': 1, 'R_index': 2, 'R_middle': 4, 'R_ring': 8,
             'R_pinky': 16, 'L_thumb': 32, 'L_index': 64,
             'L_middle': 128, 'L_ring': 256, 'L_pinky': 512}

# Presses of one button only
r_thumb = mne.pick_events(buttons, include=button_id['R_thumb'])

# One button's presses even while another is held down
# (a held button adds its bit: R_index during R_thumb reads 3, not 2)
r_index = mne.find_events(raw, stim_channel='STI_BTN',
                          mask=button_id['R_index'], mask_type='and')

# Button releases instead of presses
releases = mne.find_events(raw, stim_channel='STI_BTN', output='offset')

# Reaction time: first press after each stimulus (seconds)
idx = np.searchsorted(buttons[:, 0], events[:, 0])
ok = idx < len(buttons)
rt = (buttons[idx[ok], 0] - events[ok, 0]) / raw.info['sfreq']

# Epoch around stimulus codes (use your own codes and names)
epochs = mne.Epochs(raw, events, event_id={'face': 5, 'house': 17},
                    tmin=-0.2, tmax=0.8, picks='mag')

# Check events visually
mne.viz.plot_events(events, raw.info['sfreq'], first_samp=raw.first_samp)
raw.plot(events=events)
```

## How the MEG values are stored

This section only matters if you inspect the FIF at a low level or compare it with other converters. In MNE, `raw.get_data()` returns MEG channels in tesla either way.

**From voltage to field.** Each OPM axis outputs a voltage proportional to the magnetic field, and Cerca records that voltage. The gain in `channels.tsv` (2.7 V/nT at the standard setting) converts it:

```
field (T) = voltage (V) × 1e-9 / gain (V/nT)
```

**What "cal" is.** A FIF file stores each channel as a series of numbers plus a per-channel calibration factor, `cal`. When MNE loads the file, it multiplies the stored numbers by `cal` to get physical units. You can see it as `raw.info['chs'][i]['cal']`.

**The two ways to store the same data:**

| | Numbers stored in the file | `cal` | What MNE gives you |
|---|---|---|---|
| Original script (v2.1) | voltage (V) | 1e-9 / gain ≈ 3.7e-10 | tesla |
| This script (v2.9+) | field (T) | 1 | tesla |

**Why this script uses `cal = 1`.** The FIF format always saves `cal` in single precision, even when the data are saved in double precision. A `cal` like 3.7e-10 is therefore slightly rounded (by about 3 parts in 100 million), and that rounding is applied to every sample when the file is loaded. That defeats the purpose of `--double`. A `cal` of exactly 1 has no rounding, so `--double` output matches the original recording exactly.

In practice:
- For analysis there is no difference. The effect is far below sensor noise, and MNE's loaded values are the same either way.
- To recover the original recorded voltage of an MEG channel, multiply the tesla value by `1e9 × gain` (e.g. × 2.7e9).
- Trigger and BNC channels are stored as recorded, in volts, also with `cal = 1`. `STI101` and `STI_BTN` hold integer event codes.

## Notes

- **Units:** helmet positions and digitisation must be in metres. The script warns if values look like millimetres.
- **Gain:** the `channels.tsv` gain column (`V0x2FnT` in current Cerca exports) is in V/nT; see [How the MEG values are stored](#how-the-meg-values-are-stored).
- **Coil type:** OPM sensors use MNE's `QUSPIN_ZFOPM_MAG2` coil definition.
- **Line frequency:** this defaults to 60 Hz for North American sites; use `--line-freq 50` elsewhere.
- **Empty room:** empty-room recordings should be converted without `--xfm`/`--dig`, so they carry no head transform.
- **Memory:** usage is roughly the size of the raw data (about 7.7 GB per hour at 222 channels, 1200 Hz), and it is printed before reading.

## Troubleshooting

| Message | Meaning |
|---|---|
| `Output already exists (use --force to overwrite)` | A FIF or log from an earlier run is present. Add `--force` to replace it. |
| `Part numbering ... is incomplete` | A part such as `_meg_002.cMEG` is missing. The script won't join an incomplete recording. |
| `Time jumps by ... at the start of part NNN` | Consecutive parts aren't contiguous in time. Check the acquisition. |
| `JSON RecordingDuration=... but data contains ...` | The data read doesn't match the recorded duration. Check for missing or truncated parts. |
| `... unused (swing ... V)` on a trigger or button | That line never changed during the recording. This is expected for unused bits or buttons, but not for lines your paradigm uses. |
| `Peripherals file lists "...", which is not in channels.tsv` | A name in the peripherals file doesn't match a BNC channel. Check the spelling. |
| `--session-info file not found: ...` | The file given with `--session-info` doesn't exist. Check the path. |
| `--timezone: unknown time zone "..."` | The name isn't a valid IANA time zone. Use a name such as `America/New_York`. On Windows, also run `pip install tzdata`. |
| `File-name prefix "..." is not a YYYYMMDD_HHMMSS timestamp` | The file was renamed, so its name can't give the start time. If `SessionInfo.txt` is present, its time is used without a cross-check; otherwise the FIF is saved without a recording date. |
| `Recording start disagrees: SessionInfo says ..., the file name says ...` | The two sources differ by more than 5 s. A whole number of hours usually means a wrong `--timezone` or PC time-zone setting; anything else usually means a renamed file. The `SessionInfo.txt` time is used. |
| `..._SessionInfo.txt: invalid date/time` or `no "recording started ..." line` | The start time in `SessionInfo.txt` couldn't be read. The file-name time is used instead. |
| `SessionInfo says "Room Degaussed: No"` | The room wasn't degaussed before this recording. Expect higher residual fields and more low-frequency noise. |
| `Recording type disagrees: JSON RecordingType ..., SessionInfo Experiment Type ...` | One file calls the run empty room (`Noise`) and the other subject (`Measurement`). Check which is right. |
| `This is an empty-room recording but digitisation is being added` | `--xfm`/`--dig` were given for an empty-room run. Leave them out unless intended. |
| `This is a subject recording but no digitisation was given` | The FIF will have no head coregistration. Add `--xfm` and `--dig` unless intended. |
| `... MEG channel gain(s) in channels.tsv differ from SessionInfo "OPM V/nT: ..."` | The gain in `channels.tsv` doesn't match the one in `SessionInfo.txt`. The `channels.tsv` value is used; check which is correct for the sensors' gain setting. |

## Credits

Original `cMEG2fif` conversion script: Molly Rea, 2023. The script's docstring lists all changes since v2.1.
