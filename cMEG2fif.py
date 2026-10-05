# -*- coding: utf-8 -*-
"""
cMEG -> FIF converter  (Cerca / QuSpin OPM-MEG)

Version: see __version__ below, `python cMEG2fif.py --version`, or the
header of any conversion log.

Original v2.1: Molly Rea, 2023-05-19

Usage
-----
    python cMEG2fif.py CMEG_FILE [options]

    CMEG_FILE is any part of the recording (<prefix>_meg_001.cMEG, ...).
    Run with -h for the option list.

Requirements
------------
    pip install numpy pandas mne pyvista pyvistaqt pyqt6

numpy, pandas and mne are needed for conversion (mne brings scipy and
matplotlib). pyvista, pyvistaqt and a Qt binding (pyqt6, pyqt5 or pyside6)
are needed only for the 3D alignment plot shown when --dig is used; without
them, use --no-plot. With conda: conda install -c conda-forge mne (includes
the plotting packages).

Examples
--------
macOS/Linux shown; in the Windows command prompt end continued lines with ^
instead of a backslash. <prefix>_SessionInfo.txt is found automatically;
--session-info is only needed when it has a different name or location.

    # Empty-room recording
    python cMEG2fif.py 20260924_103257_meg_001.cMEG

    # Subject recording with head coregistration
    python cMEG2fif.py 20260924_113141_meg_001.cMEG \\
        --xfm subject003_headHelmet_dev2head_xfm.tsv \\
        --dig subject003_headHelmet_digitisation_from_mesh_3_xfmd.xyz

    # SessionInfo.txt kept elsewhere or renamed
    python cMEG2fif.py 20260924_113141_meg_001.cMEG \\
        --session-info ../session_notes/20260924_113141_SessionInfo.txt \\
        --xfm subject003_headHelmet_dev2head_xfm.tsv \\
        --dig subject003_headHelmet_digitisation_from_mesh_3_xfmd.xyz

    # Re-convert, replacing earlier output, without the 3D plot
    python cMEG2fif.py 20260924_113141_meg_001.cMEG --xfm ... --dig ... \\
        --force --no-plot

Data files
----------
Cerca writes the original recording as <prefix>_meg_001.cMEG, and long
recordings continue in <prefix>_meg_002.cMEG, _003, ... . Pick any part;
all parts are found, checked for gaps in numbering and time, and joined
into one recording. An unnumbered <prefix>_meg.cMEG is never used (it may
be an edited copy, not the original).

Sidecars (same folder, shared <prefix>)
--------------------------------------
    <prefix>_meg.json            SamplingFrequency, RecordingDuration, ...
    <prefix>_channels.tsv        name, type, gain (V/nT), status
    <prefix>_HelmConfig.tsv      Sensor, Name, Px Py Pz, Ox Oy Oz
    <prefix>_SessionInfo.txt     optional (or --session-info FILE): start
                                 time (UTC), Operator ->
                                 experimenter, Comments -> description, and
                                 checks of OPM V/nT, Room Degaussed and
                                 Experiment Type; all fields are logged
    --xfm FILE                   4x4 device->digitisation transform
                                 (default <prefix>_SensorTransform.tsv;
                                 needed only with digitisation)
    --dig FILE                   head shape .xyz, last 3 rows NAS, LPA, RPA
                                 (default <prefix>_digitisation.xyz; optional)

Output
------
<prefix>_meg.fif (or --out). FIF files are limited to 2 GB; larger
recordings are split by MNE into <prefix>_meg.fif, <prefix>_meg-1.fif, ...
Reading the first file with mne.io.read_raw_fif loads all of them.

Recording date
--------------
Cerca stores no date inside the .cMEG data. The recording start is taken
from, in order of preference:
  1. <prefix>_SessionInfo.txt, line "recording started DD/MM/YYYY -
     HH:MM:SS", already in UTC. Parsed explicitly as day/month/year.
  2. The file-name prefix YYYYMMDD_HHMMSS, local time on the acquisition PC,
     converted to UTC with --timezone (daylight saving handled).
When both are available they are compared; if they differ by more than
5 s, a warning is logged (a renamed file, a wrong --timezone, or a
mis-set PC clock). The result is stored as the FIF's meas_date, which
MNE-BIDS uses for scans.tsv acq_time and for anonymisation. With neither
source, meas_date is left unset, with a warning.

Trigger, button and auxiliary channels
--------------------------------------
Trigger 1-8 (VPixx Pixel Mode lines) stay as individual stim channels and
are also combined into STI101: Trigger 1 = 1, Trigger 2 = 2, ... Trigger 8
= 128. mne.find_events(raw) uses STI101 automatically.

Every BNC channel in use is defined in a peripherals file
(cMEG_peripherals.tsv; see --peripherals). Columns: channel, type, name.
Types:
    button  individual stim channel + a bit in the combined STI_BTN channel
            (first button listed = 1, second = 2, third = 4, ...)
    stim    individual stim channel only
    misc    kept as a misc channel (analog signals: eye tracker, etc.)
    drop    removed from the output
BNC channels not in the file are kept as misc. 'name' renames the channel.

Line levels are detected from the data, since trigger/button voltages
aren't recorded: for each line, the resting level is its median, polarity
comes from which direction it deviates most, and the threshold is half of
that swing. A line whose swing is under 0.5 V is treated as unused. Levels
are printed so the actual voltages can be checked. Transitions shorter than
3 samples (e.g. one line switching a sample before the others) are merged
into the neighbouring value; use --min-samples to change that.

Output files and logging
------------------------
Existing outputs are never overwritten unless --force is given; the check
runs before any data is read. Everything printed on screen (including
warnings and MNE messages) is also written to
<output stem>_conversion_log.txt, which starts with a provenance header:
script version and path, date/time, command line, host, and Python / MNE /
NumPy / pandas versions.

Finding events in the converted FIF
-----------------------------------
    import numpy as np
    import mne

    raw = mne.io.read_raw_fif('20260924_113141_meg.fif')

    # VPixx stimulus codes. STI101 is MNE's default stim channel, so these
    # two lines are equivalent:
    events = mne.find_events(raw)
    events = mne.find_events(raw, stim_channel='STI101')

    # If a code can change directly to another without returning to 0
    # (e.g. 5 -> 3), add consecutive=True or the second code is missed:
    events = mne.find_events(raw, consecutive=True)

    # Button presses. The event code says which button (bit values):
    buttons = mne.find_events(raw, stim_channel='STI_BTN')
    button_id = {'R_thumb': 1, 'R_index': 2, 'R_middle': 4, 'R_ring': 8,
                 'R_pinky': 16, 'L_thumb': 32, 'L_index': 64,
                 'L_middle': 128, 'L_ring': 256, 'L_pinky': 512}

    # Presses of one button only:
    r_thumb = mne.pick_events(buttons, include=button_id['R_thumb'])

    # One button's presses even while another button is held down (a held
    # button adds its bit, so R_index pressed during R_thumb reads 3, not 2):
    r_index = mne.find_events(raw, stim_channel='STI_BTN',
                              mask=button_id['R_index'], mask_type='and')

    # Button releases instead of presses:
    releases = mne.find_events(raw, stim_channel='STI_BTN', output='offset')

    # Reaction time: first press after each stimulus (seconds)
    idx = np.searchsorted(buttons[:, 0], events[:, 0])
    ok = idx < len(buttons)
    rt = (buttons[idx[ok], 0] - events[ok, 0]) / raw.info['sfreq']

    # Epoch around stimulus codes (replace with your own codes/names):
    epochs = mne.Epochs(raw, events, event_id={'face': 5, 'house': 17},
                        tmin=-0.2, tmax=0.8, picks='mag')

    # Check events visually:
    mne.viz.plot_events(events, raw.info['sfreq'], first_samp=raw.first_samp)
    raw.plot(events=events)

The button values above match the current cMEG_peripherals.tsv (first
button listed = 1, then 2, 4, ...); the conversion log lists them for each
run.

Options
-------
Inputs
    CMEG_FILE           any part of the recording (required)
    --xfm FILE          4x4 device->digitisation transform, e.g. the Cerca
                        headHelmet *_dev2head_xfm.tsv
                        (default <prefix>_SensorTransform.tsv; used only
                        with digitisation; leave out for empty-room
                        recordings)
    --dig FILE          digitisation .xyz; last 3 rows NAS, LPA, RPA
                        (default <prefix>_digitisation.xyz; optional; leave
                        out for empty-room recordings)
    --session-info FILE Cerca session file: recording start time (UTC),
                        operator, comments, OPM gain and session checks
                        (default <prefix>_SessionInfo.txt; optional; if
                        missing, the file name gives the recording date)
    --peripherals FILE  BNC peripherals file (default cMEG_peripherals.tsv in
                        the data folder, else next to this script, else the
                        copy installed with the package)
Output
    --out FILE          output FIF (default <prefix>_meg.fif); the log is
                        written next to it as <stem>_conversion_log.txt
    --force             overwrite an existing FIF, its split parts and log
    --double            store data as float64 instead of float32 (twice the
                        file size; float32 rounding, ~6e-8 of each value, is
                        far below OPM sensor noise)
Processing
    --line-freq HZ      mains frequency (default 60; JSON value is ignored)
    --timezone TZ       time zone of the acquisition PC clock, used to turn
                        the file-name timestamp into UTC (IANA name; default
                        America/New_York). Used for the recording date only
                        when SessionInfo.txt has none, and otherwise to
                        cross-check it.
    --min-samples N     shortest code kept in STI101/STI_BTN, in samples
                        (default 3)
    --max-hsp N         keep a random subset of at most N head-shape points
                        (fixed seed, so the same points every run; NAS/LPA/
                        RPA always kept; default 0 = keep all). Useful for
                        dense mesh-derived head shapes (~50k points), which
                        slow plotting and MRI coregistration.
Display
    --no-plot           skip the 3D sensor/head alignment plot (shown only
                        when digitisation is used)
    -h, --help          show the option list and exit
    --version           show the script version and exit

Changes from v2.1
-----------------
Data reading
  - Block headers are read as big-endian uint32. v2.1's conversion table
    used XOR (2^16, 2^8) and the wrong top weight, misreading any block with
    more than 255 channels or samples.
  - All numbered parts are joined; parts are streamed into one preallocated
    array (no second full-size copy), and scaling is done in place.
  - Truncated blocks, inconsistent channel counts, missing part numbers and
    time discontinuities between parts are reported.
Channels and sensors
  - Gain column accepted as V0x2FnT (current Cerca), V/nT, nT/V or nT0x2FV;
    used as V/nT (T = V * 1e-9 / gain).
  - HelmConfig footer row ('Helmet: <name> ...') and other non-numeric rows
    dropped; helmet name printed.
  - Channel -> HelmConfig matching no longer crashes on duplicate matches
    and uses integer indexing (newer pandas).
  - MEGMAG channels with no helmet slot are typed ref_meg from the start.
  - Unrecognised channel types become misc instead of crashing.
  - MISC (BNC) channels are misc by default (v2.1 typed them stim), with a
    peripherals file for buttons/renames/drops; combined STI101 and STI_BTN
    channels are added.
  - Zero-length orientations treated as unlocated; degenerate coil-frame
    handedness fixed.
  - channels.tsv status 'bad' -> info['bads'].
Metadata
  - line_freq defaults to 60 Hz (Cerca writes PowerLineFrequency as 0).
  - TaskDescription (and SessionInfo Comments) copied into
    info['description'] (the source files are unchanged).
  - meas_date set from the file-name timestamp, using --timezone (v2.12).
  - meas_date taken from SessionInfo.txt (UTC) when present, with the file
    name as fallback and a warning when they disagree; SessionInfo fields
    are logged and its OPM V/nT is checked against channels.tsv (v2.13).
  - --session-info FILE to use a SessionInfo.txt with a different name or
    location (v2.14).
  - SessionInfo Operator -> info['experimenter']; its Comments are appended
    to info['description']; warnings for "Room Degaussed: No" and for a
    recording type that doesn't match the use of --dig (v2.13).
  - Checks: data channels vs channels.tsv rows, JSON sampling rate vs time
    vector, JSON RecordingDuration vs samples read, mm-vs-m units.
Digitisation
  - --xfm / --dig for coreg files that don't share the recording prefix.
  - Fiducials no longer duplicated into the head shape; MEG positions no
    longer passed to the montage (they live in info['chs']).
  - Deprecated pandas delim_whitespace replaced; only x y z columns read.
Usability
  - --xfm without digitisation now warns instead of being silently ignored.
  - --double stores float64 data (default float32). MEG channels are stored
    in tesla with cal = 1 (v2.1 stored volts with cal = 1e-9/gain, and FIF
    keeps cal as float32, which added rounding even to double output).
  - Outputs are not overwritten without --force; screen output is saved to
    a conversion log with a provenance header.
  - Script file is cMEG2fif.py (no version in the name); the version is
    shown by --version and in every conversion log header.
  - Command-line only (the tkinter file dialog was removed); missing
    sidecars listed up front.
  - FIF saved before plotting, so a 3D-backend problem can't lose it.
  - Removed os.chdir, unused code, the Axes3D import and per-channel prints.
"""

import argparse
import atexit
import datetime
import glob
import json
import os
import platform
import re
import sys
import warnings
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__version__ = '2.14'


class _Tee:
    """Copy everything written to stdout/stderr into the log file. Output
    before the log is opened is buffered and written first."""
    fh = None
    buffer = []

    def __init__(self, stream):
        self.stream = stream

    def write(self, text):
        self.stream.write(text)
        if _Tee.fh is not None:
            _Tee.fh.write(text)
        else:
            _Tee.buffer.append(text)
        return len(text)

    def flush(self):
        self.stream.flush()
        if _Tee.fh is not None:
            _Tee.fh.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)

    @classmethod
    def open(cls, path):
        cls.fh = open(path, 'w', encoding='utf-8')
        cls.fh.write(''.join(cls.buffer))
        cls.buffer = []
        atexit.register(cls.close)

    @classmethod
    def close(cls):
        fh, cls.fh = cls.fh, None       # stop writing before closing
        if fh is not None:
            fh.flush()
            fh.close()


# Installed before importing MNE so its logger writes through the tee too.
sys.stdout = _Tee(sys.stdout)
sys.stderr = _Tee(sys.stderr)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import mne  # noqa: E402
from mne.io.constants import FIFF  # noqa: E402

PART_RE = re.compile(r'^(?P<prefix>.+)_meg_(?P<part>\d+)\.cMEG$', re.I)
UNNUM_RE = re.compile(r'^(?P<prefix>.+)_meg\.cMEG$', re.I)
GAIN_COLS = ['V0x2FnT', 'V/nT', 'nT/V', 'nT0x2FV']
GEOM_COLS = ['Px', 'Py', 'Pz', 'Ox', 'Oy', 'Oz']
MAP_NAME = 'cMEG_peripherals.tsv'
MIN_SWING = 0.5     # V; smaller swings mean the line is unused
PREFIX_TIME_RE = re.compile(r'^(\d{8}_\d{6})$')  # Cerca: YYYYMMDD_HHMMSS
DEFAULT_TZ = 'America/New_York'   # Scully Center acquisition PC
# SessionInfo.txt: "MEG Data, recording started 29/09/2026 - 17:40:22" (UTC,
# day/month/year). Parsed explicitly so early-month dates can't swap.
SESSION_TIME_RE = re.compile(
    r'recording started\s+(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*'
    r'(\d{1,2}):(\d{2}):(\d{2})', re.I)
DATE_TOLERANCE_S = 5   # allowed SessionInfo vs file-name difference


# --------------------------------------------------------------------------
# File discovery and reading
# --------------------------------------------------------------------------
def find_parts(path):
    """Return (prefix_path, [part paths in order]) for the recording that
    `path` belongs to. Only numbered originals (_meg_NNN.cMEG) are used."""
    path = os.path.abspath(path)
    folder, base = os.path.split(path)
    m = PART_RE.match(base)
    if m is None:
        m = UNNUM_RE.match(base)
        if m is None:
            sys.exit(f'Not a cMEG data file (<prefix>_meg_NNN.cMEG): {path}')
        print(f'Ignoring {base}: unnumbered files may be edited copies. '
              f'Looking for the original numbered parts instead.')
    stem = m.group('prefix')

    parts = []
    for f in os.listdir(folder):
        mm = PART_RE.match(f)
        if mm and mm.group('prefix') == stem:
            parts.append((int(mm.group('part')), f))
    if not parts:
        sys.exit(f'No original {stem}_meg_NNN.cMEG files found in {folder}')
    parts.sort()
    nums = [n for n, _ in parts]
    if nums != list(range(1, len(nums) + 1)):
        sys.exit(f'Part numbering for {stem} is incomplete: found '
                 f'{[f for _, f in parts]} (expected _meg_001 onward with '
                 f'no gaps). Refusing to join an incomplete recording.')
    for f in os.listdir(folder):
        mm = UNNUM_RE.match(f)
        if mm and mm.group('prefix') == stem:
            print(f'Note: ignoring {f} (not an original numbered part).')
    return os.path.join(folder, stem), [os.path.join(folder, f)
                                        for _, f in parts]


def scan_cmeg(filename):
    """List (data_offset, n_ch, n_samp) for each block without reading data.
    Blocks are [uint32 n_ch][uint32 n_samp][n_ch*n_samp float64], big-endian."""
    size = os.path.getsize(filename)
    blocks = []
    with open(filename, 'rb') as fid:
        pos = 0
        while pos < size:
            hdr = np.fromfile(fid, '>u4', count=2)
            if hdr.size < 2:
                raise ValueError(f'{os.path.basename(filename)}: truncated '
                                 f'block header at byte {pos}')
            n_ch, n_samp = int(hdr[0]), int(hdr[1])
            nbytes = n_ch * n_samp * 8
            if pos + 8 + nbytes > size:
                raise ValueError(
                    f'{os.path.basename(filename)}: block at byte {pos} '
                    f'claims {n_ch} ch x {n_samp} samples but the file ends '
                    f'{pos + 8 + nbytes - size} bytes early')
            blocks.append((pos + 8, n_ch, n_samp))
            pos += 8 + nbytes
            fid.seek(pos)
    if not blocks:
        raise ValueError(f'No data blocks in {filename}')
    return blocks


def read_parts(files, extra_rows=0):
    """Read all parts into one (n_rows, n_samples) float64 array.
    `extra_rows` empty rows are appended for derived channels.
    Returns (array, sample index where each part starts)."""
    scans = [scan_cmeg(f) for f in files]
    n_rows = {b[1] for s in scans for b in s}
    if len(n_rows) > 1:
        raise ValueError(f'Inconsistent channel counts across blocks/parts: '
                         f'{sorted(n_rows)}')
    n_rows = n_rows.pop()
    part_len = [sum(b[2] for b in s) for s in scans]
    total = sum(part_len)
    gb = n_rows * total * 8 / 1e9
    print(f'  {len(files)} part(s), {n_rows - 1} channels, {total} samples '
          f'({gb:.1f} GB in memory)')
    out = np.empty((n_rows + extra_rows, total), dtype=np.float64)
    starts, col = [], 0
    for f, s in zip(files, scans):
        starts.append(col)
        print(f'  reading {os.path.basename(f)}')
        with open(f, 'rb') as fid:
            for off, n_ch, n_samp in s:
                fid.seek(off)
                block = np.fromfile(fid, '>f8', count=n_ch * n_samp)
                out[:n_rows, col:col + n_samp] = block.reshape(n_ch, n_samp)
                col += n_samp
    return out, starts


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _norm(s):
    return re.sub(r'[\W_]+', '', str(s))


def _calc_tangent(ez):
    """Two unit vectors orthogonal to unit vector ez, giving a right-handed
    (ex, ey, ez) frame."""
    x, y, z = ez
    r = np.sqrt(x * x + y * y + z * z)
    if x == 0 and y == 0:
        ex = np.array([1.0, 0.0, 0.0])
        ey = np.array([0.0, 1.0 if z > 0 else -1.0, 0.0])
        return ex, ey
    rzxy = -(r - z) * x * y
    x2y2 = 1 / (x * x + y * y)
    ex = np.array([(z * x * x + r * y * y) * x2y2 / r,
                   rzxy * x2y2 / r,
                   -x / r])
    ey = np.array([rzxy * x2y2 / r,
                   (z * y * y + r * x * x) * x2y2 / r,
                   -y / r])
    return ex, ey


def _chkey(s):
    """Channel-name key ignoring axis tags and punctuation: 'BNC 1 [Z]' ->
    'BNC1'."""
    return _norm(re.sub(r'\[[^\]]*\]', '', str(s))).upper()


def load_peripherals(path):
    """Return an ordered dict {key: (type, new_name, original label)}."""
    m = pd.read_csv(path, sep='\t', comment='#', dtype=str).fillna('')
    m.columns = m.columns.str.strip().str.lower()
    if not {'channel', 'type'} <= set(m.columns):
        sys.exit(f'{path}: needs "channel" and "type" columns')
    out = {}
    for _, r in m.iterrows():
        typ = r['type'].strip().lower()
        if typ not in ('button', 'stim', 'misc', 'drop'):
            sys.exit(f'{path}: unknown type "{typ}" for {r["channel"]}')
        key = _chkey(r['channel'])
        if key in out:
            sys.exit(f'{path}: {r["channel"]} listed twice')
        out[key] = (typ, str(r.get('name', '')).strip(), r['channel'].strip())
    return out


def binarize(x, label):
    """Threshold one analog line to on/off with auto-detected level and
    polarity. Returns (bool array or None if unused, description)."""
    step = max(1, x.size // 200000)
    rest = float(np.median(x[::step]))
    up, down = float(x.max()) - rest, rest - float(x.min())
    swing = max(up, down)
    if swing < MIN_SWING:
        return None, f'{label}: unused (swing {swing:.3f} V)'
    if up >= down:
        return (x > rest + up / 2,
                f'{label}: rest {rest:.2f} V, active-high to {rest + up:.2f} V')
    return (x < rest - down / 2,
            f'{label}: rest {rest:.2f} V, active-low to {rest - down:.2f} V')


def combine_bits(lines, labels, n_samp, min_len):
    """Combine lines (bit k = 2**k) into one integer code channel and merge
    runs shorter than min_len samples into the following value."""
    code = np.zeros(n_samp, dtype=np.int32)
    for k, (x, lab) in enumerate(zip(lines, labels)):
        b, msg = binarize(x, lab)
        print(f'    bit {1 << k:>4}  {msg}')
        if b is not None:
            code |= b.astype(np.int32) << k
    if min_len > 1:
        change = np.flatnonzero(np.diff(code)) + 1
        if change.size:
            starts = np.r_[0, change]
            lens = np.diff(np.r_[starts, n_samp])
            vals = code[starts]
            for r in range(len(vals) - 2, 0, -1):
                if lens[r] < min_len:
                    vals[r] = vals[r + 1]
            code = np.repeat(vals, lens)
    return code


def start_time_from_prefix(prefix, tz_name):
    """Recording start from the Cerca file-name prefix.

    Cerca names each recording after the moment it started, as local time on
    the acquisition PC (YYYYMMDD_HHMMSS). Returns (start in UTC, start in
    local time), or (None, None) if the prefix isn't such a timestamp.
    """
    m = PREFIX_TIME_RE.match(os.path.basename(prefix))
    if not m:
        return None, None
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        sys.exit(f'--timezone: unknown time zone "{tz_name}". Use an IANA '
                 f'name such as America/New_York (on Windows, also run '
                 f'"pip install tzdata").')
    try:
        naive = datetime.datetime.strptime(m.group(1), '%Y%m%d_%H%M%S')
    except ValueError:
        return None, None
    local = naive.replace(tzinfo=tz)
    return local.astimezone(datetime.timezone.utc), local


def read_session_info(path):
    """Read Cerca's <prefix>_SessionInfo.txt.

    Returns (fields, start_utc, problem): the 'Key: value' lines as a dict,
    the recording start as a UTC datetime (or None), and a description of
    why the start couldn't be read (or None).
    """
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        text = f.read()
    fields = {}
    for line in text.splitlines():
        if SESSION_TIME_RE.search(line) or ':' not in line:
            continue
        key, value = line.split(':', 1)
        if key.strip():
            fields[key.strip()] = value.strip()
    m = SESSION_TIME_RE.search(text)
    if not m:
        return fields, None, ('no "recording started DD/MM/YYYY - HH:MM:SS" '
                              'line')
    day, month, year, hh, mm, ss = (int(g) for g in m.groups())
    try:
        start = datetime.datetime(year, month, day, hh, mm, ss,
                                  tzinfo=datetime.timezone.utc)
    except ValueError:
        return fields, None, f'invalid date/time in "{m.group(0)}"'
    return fields, start, None


def _require(paths):
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        sys.exit('Missing required file(s):\n  ' + '\n  '.join(missing))


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=f'Convert Cerca/QuSpin OPM-MEG .cMEG recordings to MNE '
                    f'FIF (version {__version__}). See the top of this script '
                    f'for full documentation.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''examples (macOS/Linux; in the Windows command prompt use ^ instead of \\):
  empty room:  %(prog)s 20260924_103257_meg_001.cMEG
  subject:     %(prog)s 20260924_113141_meg_001.cMEG \\
                   --xfm subject003_headHelmet_dev2head_xfm.tsv \\
                   --dig subject003_headHelmet_digitisation_from_mesh_3_xfmd.xyz
''')
    ap.add_argument('--version', action='version',
                    version=f'%(prog)s {__version__}')
    ap.add_argument('cmeg', metavar='CMEG_FILE',
                    help='any part of the recording (<prefix>_meg_NNN.cMEG)')
    g = ap.add_argument_group('inputs')
    g.add_argument('--xfm', metavar='FILE',
                   help='4x4 device->digitisation transform (default '
                        '<prefix>_SensorTransform.tsv; used only with '
                        '--dig; omit for empty room)')
    g.add_argument('--dig', metavar='FILE',
                   help='digitisation .xyz, last 3 rows NAS/LPA/RPA (default '
                        '<prefix>_digitisation.xyz; omit for empty room)')
    g.add_argument('--session-info', metavar='FILE',
                   help='Cerca SessionInfo.txt: recording start (UTC), '
                        'operator, comments, session checks (default '
                        '<prefix>_SessionInfo.txt; optional)')
    g.add_argument('--peripherals', metavar='FILE',
                   help=f'BNC peripherals file (default {MAP_NAME} in the '
                        f'data folder, else next to this script, else the '
                        f'copy installed with the package)')
    g = ap.add_argument_group('output')
    g.add_argument('--out', metavar='FILE',
                   help='output FIF (default <prefix>_meg.fif); log goes '
                        'next to it')
    g.add_argument('--force', action='store_true',
                   help='overwrite an existing FIF, its split parts and log')
    g.add_argument('--double', action='store_true',
                   help='store data as float64 instead of float32 '
                        '(twice the file size)')
    g = ap.add_argument_group('processing')
    g.add_argument('--line-freq', metavar='HZ', type=float, default=60.0,
                   help='mains frequency (default 60; JSON value ignored)')
    g.add_argument('--timezone', metavar='TZ', default=DEFAULT_TZ,
                   help='time zone of the acquisition PC clock, used to turn '
                        'the file-name timestamp into UTC: the recording date '
                        'when SessionInfo.txt has none, otherwise a '
                        f'cross-check (IANA name; default {DEFAULT_TZ})')
    g.add_argument('--min-samples', metavar='N', type=int, default=3,
                   help='shortest code kept in STI101/STI_BTN (default 3)')
    g.add_argument('--max-hsp', metavar='N', type=int, default=0,
                   help='keep a random subset of at most N head-shape points '
                        '(fixed seed, so the same points every run; '
                        'fiducials always kept; default 0 = all)')
    g = ap.add_argument_group('display')
    g.add_argument('--no-plot', action='store_true',
                   help='skip the 3D sensor/head alignment plot')
    args = ap.parse_args()

    now = datetime.datetime.now().astimezone()
    print(f'cMEG2fif version {__version__}')
    print(f'  Run:      {now:%Y-%m-%d %H:%M:%S %Z}')
    print(f'  Command:  {" ".join(sys.argv)}')
    print(f'  Script:   {os.path.abspath(__file__)}')
    print(f'  Host:     {platform.node()} ({platform.platform()})')
    print(f'  Versions: Python {platform.python_version()}, '
          f'MNE {mne.__version__}, NumPy {np.__version__}, '
          f'pandas {pd.__version__}')
    print(f'  Output:   ' + ('double precision (float64)' if args.double
                             else 'single precision (float32, default)'))
    print()

    prefix, parts = find_parts(args.cmeg)

    json_path = prefix + '_meg.json'
    chan_path = prefix + '_channels.tsv'
    helm_path = prefix + '_HelmConfig.tsv'
    xfm_path = args.xfm or prefix + '_SensorTransform.tsv'
    dig_path = args.dig or prefix + '_digitisation.xyz'
    out_path = os.path.abspath(args.out or prefix + '_meg.fif')
    stem = out_path[:-4] if out_path.lower().endswith('.fif') else out_path
    log_path = stem + '_conversion_log.txt'
    split_re = re.compile(re.escape(os.path.basename(stem)) + r'-\d+\.fif$')
    old_splits = [os.path.join(os.path.dirname(stem), f)
                  for f in os.listdir(os.path.dirname(stem))
                  if split_re.match(f)]
    existing = [f for f in [out_path, log_path] if os.path.exists(f)] \
        + old_splits
    if existing and not args.force:
        sys.exit('Output already exists (use --force to overwrite):\n  '
                 + '\n  '.join(existing))
    _Tee.open(log_path)
    print(f'Log: {log_path}')
    print(f'Input parts: {", ".join(os.path.basename(p) for p in parts)}')
    # ---------------- Recording start ----------------
    session_path = args.session_info or prefix + '_SessionInfo.txt'
    if args.session_info and not os.path.isfile(session_path):
        sys.exit(f'--session-info file not found: {session_path}')
    sess_fields, sess_utc = {}, None
    if os.path.isfile(session_path):
        sess_fields, sess_utc, problem = read_session_info(session_path)
        print(f'Session info: {os.path.basename(session_path)}')
        for key, value in sess_fields.items():
            print(f'    {key}: {value}')
        if problem:
            warnings.warn(f'{os.path.basename(session_path)}: {problem}; '
                          f'using the file name for the recording date.')
    else:
        print(f'No {os.path.basename(session_path)} found; using the file '
              f'name for the recording date.')
    file_utc, file_local = start_time_from_prefix(prefix, args.timezone)
    if sess_utc is not None:
        print(f'Recording start (from SessionInfo, UTC): '
              f'{sess_utc:%Y-%m-%d %H:%M:%S} UTC')
    if file_utc is not None:
        print(f'Recording start (from the file name, {args.timezone}): '
              f'{file_local:%Y-%m-%d %H:%M:%S %Z} = '
              f'{file_utc:%Y-%m-%d %H:%M:%S} UTC')
    else:
        warnings.warn(
            f'File-name prefix "{os.path.basename(prefix)}" is not a '
            f'YYYYMMDD_HHMMSS timestamp (renamed file?), so '
            + ('the SessionInfo time cannot be cross-checked.'
               if sess_utc is not None else
               'the FIF gets no recording date (meas_date).'))
    if sess_utc is not None and file_utc is not None:
        diff = (file_utc - sess_utc).total_seconds()
        if abs(diff) <= DATE_TOLERANCE_S:
            print('  File name and SessionInfo agree.')
        else:
            rem = abs(diff) % 3600
            whole_hours = abs(diff) >= 3600 - DATE_TOLERANCE_S and (
                rem <= DATE_TOLERANCE_S or rem >= 3600 - DATE_TOLERANCE_S)
            hint = (f'They differ by a whole number of hours, which usually '
                    f'means --timezone ({args.timezone}) is not the time zone '
                    f'of the acquisition PC clock, or that clock\'s time zone '
                    f'or daylight-saving setting is wrong.' if whole_hours else
                    'The file may have been renamed, or the acquisition PC '
                    'clock was changed.')
            warnings.warn(
                f'Recording start disagrees: SessionInfo says '
                f'{sess_utc:%Y-%m-%d %H:%M:%S} UTC, the file name says '
                f'{file_utc:%Y-%m-%d %H:%M:%S} UTC ({diff:+.0f} s). {hint} '
                f'Using SessionInfo.')
    if sess_utc is not None:
        meas_utc, meas_source = sess_utc, 'SessionInfo'
    elif file_utc is not None:
        meas_utc, meas_source = file_utc, 'file name'
    else:
        meas_utc, meas_source = None, None
    if args.dig and not os.path.isfile(args.dig):
        sys.exit(f'--dig file not found: {args.dig}')
    use_dig = os.path.isfile(dig_path)
    if args.xfm and not use_dig:
        warnings.warn(f'--xfm given but no digitisation found ({dig_path}); '
                      f'the transform is ignored. Add --dig, or leave out '
                      f'--xfm for empty-room recordings.')
    _require([json_path, chan_path, helm_path]
             + ([xfm_path] if use_dig else []))

    # ---------------- Sidecars ----------------
    with open(json_path) as f:
        meta = json.load(f)
    sfreq = float(meta['SamplingFrequency'])

    # ---------------- Session checks ----------------
    degaussed = sess_fields.get('Room Degaussed', '').strip()
    if degaussed.lower().startswith('no'):
        warnings.warn(f'SessionInfo says "Room Degaussed: {degaussed}". '
                      f'Expect higher residual fields and low-frequency '
                      f'noise.')
    json_type = str(meta.get('RecordingType', '')).strip()
    sess_type = sess_fields.get('Experiment Type', '').strip()
    kinds = {}
    for src, val in (('JSON RecordingType', json_type),
                     ('SessionInfo Experiment Type', sess_type)):
        v = val.lower()
        if 'noise' in v or 'empty' in v:
            kinds[src] = ('empty room', val)
        elif 'measurement' in v:
            kinds[src] = ('subject', val)
    if len({k for k, _ in kinds.values()}) > 1:
        warnings.warn('Recording type disagrees: '
                      + ', '.join(f'{s} "{v}"' for s, (_, v) in kinds.items())
                      + '.')
    elif kinds:
        kind = next(iter(kinds.values()))[0]
        label = ', '.join(f'{s} "{v}"' for s, (_, v) in kinds.items())
        print(f'Recording type: {kind} ({label})')
        if kind == 'empty room' and use_dig:
            warnings.warn('This is an empty-room recording but digitisation '
                          'is being added. Empty-room FIFs normally carry no '
                          'head coregistration; leave out --xfm/--dig unless '
                          'this is intended.')
        elif kind == 'subject' and not use_dig:
            warnings.warn('This is a subject recording but no digitisation '
                          'was given, so the FIF has no head coregistration. '
                          'Add --xfm and --dig unless this is intended.')

    channels = pd.read_csv(chan_path, sep='\t')
    channels.columns = channels.columns.str.strip()
    gain_col = next((c for c in GAIN_COLS if c in channels.columns), None)
    if gain_col is None:
        sys.exit(f'channels.tsv has no gain column (looked for {GAIN_COLS})')
    n_ch = len(channels)

    helm = pd.read_csv(helm_path, sep='\t')
    helm.columns = helm.columns.str.strip()
    numeric = helm[GEOM_COLS].apply(pd.to_numeric, errors='coerce') \
        .notna().all(axis=1)
    footer = helm[~numeric]
    if len(footer) and str(footer.iloc[0]['Name']).strip() \
            .rstrip(':').lower() == 'helmet':
        print(f'  Helmet: {footer.iloc[0]["Px"]}')
    helm = helm[numeric].reset_index(drop=True)
    helm[GEOM_COLS] = helm[GEOM_COLS].astype(float)

    T_old = None
    if use_dig:
        T_old = (pd.read_csv(xfm_path, sep=r'\s+', header=None)
                 .dropna(axis=1, how='all').to_numpy(float))
        if T_old.shape != (4, 4):
            sys.exit(f'Sensor transform must be 4x4, got {T_old.shape}')

    # ---------------- Channel roles ----------------
    names = [str(n).replace(' ', '') for n in channels['name']]
    types = [str(s).replace(' ', '').upper() for s in channels['type']]
    map_path = args.peripherals
    if map_path is None:
        for cand in (os.path.join(os.path.dirname(prefix), MAP_NAME),
                     os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  MAP_NAME),
                     # copy installed by pip (see pyproject.toml)
                     os.path.join(sys.prefix, 'share', 'cmeg2fif', MAP_NAME)):
            if os.path.isfile(cand):
                map_path = cand
                break
    elif not os.path.isfile(map_path):
        sys.exit(f'--peripherals file not found: {map_path}')
    chmap = {}
    if map_path:
        chmap = load_peripherals(map_path)
        print(f'Peripherals: {map_path}')
    else:
        print(f'No {MAP_NAME} found; BNC channels kept as misc.')

    role = []
    keys = [_chkey(n) for n in channels['name']]
    for i, typ in enumerate(types):
        role.append({'MEGMAG': 'meg', 'TRIG': 'trig',
                     'MISC': 'misc'}.get(typ, 'other'))
        if keys[i] in chmap and typ in ('TRIG', 'MISC'):
            mtype, new_name, _ = chmap[keys[i]]
            if typ == 'TRIG' and mtype != 'drop':
                pass        # trigger lines are always stim + STI101 bits
            else:
                role[i] = mtype
            if new_name:
                names[i] = new_name
        elif keys[i] in chmap:
            warnings.warn(f'Peripherals entry for {channels["name"][i]} '
                          f'ignored (only trigger/BNC channels can be mapped).')
    for k, (_, _, label) in chmap.items():
        if k not in keys:
            warnings.warn(f'Peripherals file lists "{label}", which is not in '
                          f'channels.tsv.')
    bnc_rows = [i for i, typ in enumerate(types) if typ == 'MISC']
    if bnc_rows:
        print('BNC channels:')
        for i in bnc_rows:
            label = str(channels['name'][i]).strip()
            src = 'peripherals' if keys[i] in chmap else 'default'
            new = f' -> {names[i]}' if keys[i] in chmap and chmap[keys[i]][1] \
                else ''
            print(f'    {label:<12} {role[i]:<7} ({src}){new}')
    trig_idx = sorted((i for i, r in enumerate(role) if r == 'trig'),
                      key=lambda i: int((re.findall(r'\d+', channels['name'][i])
                                         or ['0'])[0]))
    btn_idx = [keys.index(k) for k, v in chmap.items()
               if v[0] == 'button' and k in keys
               and role[keys.index(k)] == 'button']
    derived = (['STI101'] if trig_idx else []) + (['STI_BTN'] if btn_idx else [])
    for d in derived:
        if d in names:
            sys.exit(f'Channel name {d} is reserved for the combined channel.')
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        sys.exit(f'Duplicate channel names after renaming: {sorted(dup)}')

    # ---------------- Data ----------------
    print('Loading data')
    buf, starts = read_parts(parts, extra_rows=len(derived))
    t = buf[0]
    data = buf[1:]          # view; scaled in place below
    if data.shape[0] - len(derived) != n_ch:
        sys.exit(f'Data has {data.shape[0] - len(derived)} channels '
                 f'(excluding time) but '
                 f'channels.tsv lists {n_ch}.')

    if t.size > 1:
        est = 1.0 / np.median(np.diff(t[:min(t.size, 100000)]))
        if abs(est - sfreq) / sfreq > 0.01:
            warnings.warn(f'JSON SamplingFrequency={sfreq} but time vector '
                          f'implies {est:.3f} Hz. Using JSON value.')
    for k, s0 in enumerate(starts[1:], start=2):
        step = t[s0] - t[s0 - 1]
        if abs(step - 1 / sfreq) > 0.5 / sfreq:
            warnings.warn(f'Time jumps by {step:.6f} s at the start of part '
                          f'{k:03d} (expected {1 / sfreq:.6f} s). Parts may '
                          f'not be contiguous.')
    dur = meta.get('RecordingDuration')
    if isinstance(dur, (int, float)) and dur > 0:
        got = data.shape[1] / sfreq
        if abs(got - dur) > max(1.0, 0.01 * dur):
            warnings.warn(f'JSON RecordingDuration={dur:.1f}s but data '
                          f'contains {got:.1f}s.')

    gain = pd.to_numeric(channels[gain_col], errors='coerce').to_numpy(float)
    try:
        sess_gain = float(sess_fields.get('OPM V/nT', ''))
    except ValueError:
        sess_gain = None
    if sess_gain is not None and np.isfinite(sess_gain) and sess_gain > 0:
        meg_gain = gain[[t == 'MEGMAG' for t in types]]
        off = np.abs(meg_gain - sess_gain) > 0.01 * sess_gain
        if off.any():
            warnings.warn(f'{int(off.sum())} MEG channel gain(s) in '
                          f'channels.tsv differ from SessionInfo "OPM V/nT: '
                          f'{sess_gain:g}" (channels.tsv values used: '
                          f'{", ".join(f"{v:g}" for v in sorted(set(meg_gain[off])))}).')
        else:
            print(f'  MEG gains match SessionInfo OPM V/nT ({sess_gain:g}).')

    # ---------------- Sensor geometry ----------------
    print('Matching sensors to HelmConfig')
    helm_keys = [_norm(s) for s in helm['Sensor']]
    helm_P = helm[['Px', 'Py', 'Pz']].to_numpy()
    helm_O = helm[['Ox', 'Oy', 'Oz']].to_numpy()
    pos = np.full((n_ch, 3), np.nan)
    ori = np.full((n_ch, 3), np.nan)
    for i, name in enumerate(channels['name']):
        matches = [j for j, h in enumerate(helm_keys) if h == _norm(name)]
        if len(matches) > 1:
            warnings.warn(f'{name}: {len(matches)} HelmConfig matches; '
                          f'using first ({helm["Name"].iloc[matches[0]]}).')
        if matches:
            j = matches[0]
            if np.linalg.norm(helm_O[j]) > 0 and np.all(np.isfinite(helm_P[j])):
                pos[i] = helm_P[j]
                ori[i] = helm_O[j]
            else:
                warnings.warn(f'{name}: invalid position/orientation in '
                              f'HelmConfig; treating as unlocated.')

    # ---------------- Types and scaling (in place) ----------------
    print('Scaling data and assigning channel types')
    ch_types = []
    for i, typ in enumerate(types):
        if typ == 'MEGMAG':
            if not np.isfinite(gain[i]) or gain[i] == 0:
                sys.exit(f'{names[i]}: invalid gain "{gain[i]}"')
            data[i] *= 1e-9 / gain[i]                 # V -> T
            ch_types.append('mag' if np.all(np.isfinite(pos[i]))
                            else 'ref_meg')
        elif role[i] in ('trig', 'button', 'stim'):
            ch_types.append('stim')                   # stays in V
        elif role[i] in ('misc', 'drop'):
            ch_types.append('misc')                   # stays in V
        else:
            warnings.warn(f'{names[i]}: unrecognised type "{typ}"; '
                          f'storing as misc.')
            ch_types.append('misc')

    # ---------------- Combined trigger / button channels ----------------
    row = n_ch
    if trig_idx:
        print('Building STI101 from trigger lines')
        data[row] = combine_bits([data[i] for i in trig_idx],
                                 [channels['name'][i] for i in trig_idx],
                                 data.shape[1], args.min_samples)
        row += 1
    if btn_idx:
        print('Building STI_BTN from button lines')
        data[row] = combine_bits([data[i] for i in btn_idx],
                                 [f'{names[i]} ({channels["name"][i]})'
                                  for i in btn_idx],
                                 data.shape[1], args.min_samples)
    names += derived
    ch_types += ['stim'] * len(derived)

    # ---------------- Info ----------------
    print('Creating MNE info')
    info = mne.create_info(ch_names=names, sfreq=sfreq, ch_types=ch_types)
    info['line_freq'] = args.line_freq
    info['device_info'] = {'type': 'Cerca', 'model': 'cMEG'}
    notes = []
    desc = str(meta.get('TaskDescription', '')).strip()
    if desc and desc.lower() != 'n/a':
        notes.append(desc)
        print(f'  Recording comment (JSON TaskDescription): "{desc}"')
    sess_comment = sess_fields.get('Comments', '').strip()
    if sess_comment and sess_comment.lower() != 'n/a' \
            and sess_comment not in notes:
        notes.append(sess_comment)
        print(f'  Recording comment (SessionInfo Comments): "{sess_comment}"')
    if notes:
        info['description'] = ' | '.join(notes)
        print("    -> stored in the FIF as info['description']: "
              f'"{info["description"]}"')
    else:
        print('  No recording comment (JSON TaskDescription and SessionInfo '
              'Comments are empty)')
    operator = sess_fields.get('Operator', '').strip()
    if operator and operator.lower() != 'n/a':
        info['experimenter'] = operator
        print(f"  Operator (SessionInfo) -> info['experimenter']: {operator}")

    nmeg = nref = nstim = 0
    for i, ct in enumerate(ch_types):
        ch = info['chs'][i]
        ch['scanno'] = i + 1
        if ct == 'mag':
            nmeg += 1
            ez = ori[i] / np.linalg.norm(ori[i])
            ex, ey = _calc_tangent(ez)
            ch.update(logno=nmeg, coord_frame=FIFF.FIFFV_COORD_DEVICE,
                      kind=FIFF.FIFFV_MEG_CH, unit=FIFF.FIFF_UNIT_T,
                      coil_type=FIFF.FIFFV_COIL_QUSPIN_ZFOPM_MAG2,
                      loc=np.concatenate([pos[i], ex, ey, ez]),
                      cal=1.0)   # data already in T
        elif ct == 'ref_meg':
            nref += 1
            ch.update(logno=nref, coord_frame=FIFF.FIFFV_COORD_UNKNOWN,
                      kind=FIFF.FIFFV_REF_MEG_CH, unit=FIFF.FIFF_UNIT_T,
                      coil_type=FIFF.FIFFV_COIL_QUSPIN_ZFOPM_MAG2,
                      cal=1.0)   # data already in T
        elif ct == 'stim':
            nstim += 1
            ch.update(logno=nstim, coord_frame=FIFF.FIFFV_COORD_UNKNOWN,
                      kind=FIFF.FIFFV_STIM_CH, unit=FIFF.FIFF_UNIT_V, cal=1.0)
    def _n(k, what):
        return f'{k} {what}' + ('' if k == 1 else 's')
    def _and(items):
        return (items[0] if len(items) == 1 else
                ', '.join(items[:-1]) + (',' if len(items) > 2 else '')
                + ' and ' + items[-1])
    stim_parts = []
    if trig_idx:
        stim_parts += [_n(len(trig_idx), 'VPixx trigger channel'), 'STI101']
    if btn_idx:
        stim_parts += [_n(len(btn_idx), 'BNC button channel'), 'STI_BTN']
    n_other_stim = sum(r == 'stim' for r in role)
    if n_other_stim:
        stim_parts.append(_n(n_other_stim, 'other BNC stim channel'))
    kept_misc = [i for i in range(n_ch)
                 if ch_types[i] == 'misc' and role[i] != 'drop']
    named_misc = [names[i] for i in kept_misc
                  if keys[i] in chmap and chmap[keys[i]][1]]
    n_drop = sum(r == 'drop' for r in role)
    summary = [_n(nmeg, 'MEG channel'), _n(nref, 'reference channel'),
               _n(nstim, 'stim channel')
               + (f' (incl. {_and(stim_parts)})' if stim_parts else ''),
               _n(len(kept_misc), 'misc channel')
               + (f' (incl. {_and(named_misc)})' if named_misc else '')]
    if n_drop:
        summary.append(f'{n_drop} dropped')
    print('  ' + ', '.join(summary))

    # ---------------- Digitisation ----------------
    montage = None
    if use_dig:
        print(f'Reading digitisation: {os.path.basename(dig_path)}')
        pts = pd.read_csv(dig_path, skiprows=2, sep=r'\s+', header=None,
                          usecols=[0, 1, 2]).to_numpy(float)
        pts = pts[np.all(np.isfinite(pts), axis=1)]
        if pts.shape[0] < 3:
            sys.exit('Digitisation needs at least 3 points (NAS, LPA, RPA)')
        nas, lpa, rpa = pts[-3], pts[-2], pts[-1]
        hsp = pts[:-3]
        if args.max_hsp and len(hsp) > args.max_hsp:
            keep = np.sort(np.random.default_rng(0).choice(
                len(hsp), args.max_hsp, replace=False))
            print(f'  Decimating head shape: {len(hsp)} -> {args.max_hsp}')
            hsp = hsp[keep]

        ear_dist = np.linalg.norm(lpa - rpa)
        if ear_dist > 1.0:
            warnings.warn(f'LPA-RPA distance is {ear_dist:.1f}; looks like '
                          f'mm, but MNE expects metres.')
        sens_r = np.nanmax(np.linalg.norm(pos, axis=1)) if nmeg else 0
        if sens_r > 1.0:
            warnings.warn(f'Sensor positions reach {sens_r:.1f} from origin; '
                          f'looks like mm, but MNE expects metres.')

        montage = mne.channels.make_dig_montage(
            nasion=nas, lpa=lpa, rpa=rpa,
            hsp=hsp if len(hsp) else None, coord_frame='unknown')
        T_new = mne.transforms.get_ras_to_neuromag_trans(
            nasion=nas, lpa=lpa, rpa=rpa)
        info['dev_head_t'] = mne.transforms.Transform('meg', 'head',
                                                      T_new @ T_old)
    else:
        print('No digitisation; saving without head digitisation or '
              'dev_head_t.')

    # ---------------- Raw + save ----------------
    print('Creating raw object')
    raw = mne.io.RawArray(data, info, copy='auto')
    del buf, data, t
    if meas_utc is not None:
        raw.set_meas_date(meas_utc)
        print(f'  Recording date (meas_date, from {meas_source}): '
              f'{meas_utc:%Y-%m-%d %H:%M:%S} UTC')
    dropped = [names[i] for i in range(n_ch) if role[i] == 'drop']
    if dropped:
        raw.drop_channels(dropped)
        print(f'  Dropped per peripherals file: {dropped}')
    if montage is not None:
        raw.set_montage(montage)
    if 'status' in channels.columns:
        bads = [n for n, st in zip(names, channels['status'])
                if str(st).strip().lower() == 'bad']
        raw.info['bads'] = bads
        if bads:
            print(f'  Marked bad from channels.tsv: {bads}')

    print(f'Saving {out_path}')
    written = raw.save(out_path, overwrite=args.force,        # splits at 2 GB
                       fmt='double' if args.double else 'single')
    written = [os.path.abspath(str(f)) for f in (written or [out_path])]
    stale = [f for f in old_splits if os.path.abspath(f) not in written]
    for f in stale:
        os.remove(f)
    if stale:
        print(f'  Removed split files left from the previous output: '
              f'{[os.path.basename(f) for f in stale]}')
    if len(written) > 1:
        print(f'  Output split at 2 GB into: '
              f'{[os.path.basename(f) for f in written]}')

    # ---------------- Optional plot ----------------
    if montage is not None and not args.no_plot:
        try:
            mne.viz.set_3d_backend('pyvistaqt')
            fig = mne.viz.plot_alignment(raw.info, meg='helmet', dig=True,
                                         show_axes=True, coord_frame='meg')
            if not hasattr(sys, 'ps1'):     # plain script: keep window open
                fig.plotter.app.exec_()
        except Exception as e:  # plotting must never lose the conversion
            warnings.warn(f'Alignment plot failed ({e}); FIF already saved.')

    print(f'Done. Log saved to {log_path}')
    return raw


if __name__ == '__main__':
    main()
