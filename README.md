# Quake 3 Map Demo Compatibility Checker

A Python script to quickly analyze `.pk3` map files for Quake 3 Arena and determine whether they are compatible with the demo version of Q3A or require the full game.

## Requirements

* Python 3
* Demo and Full versions of `pak0.pk3`
* Quake 3 1.32 point-release files (`pak1.pk3` to `pak7.pk3`)

## Setup

1. Place the following files in a `baseq3` folder local to the Python script:

   * `pak0-demo.pk3` (from the demo)
   * `pak0-full.pk3` (from the full version)
   * `pak1.pk3` through `pak7.pk3` (from the 1.32 [point release](https://ioquake3.org/extras/patch-data/))

2. Adjust paths in the script if necessary.

## Usage

* To analyze a local `.pk3`:

```python
MAP_PK3 = "yourmap.pk3"
```

* To download and analyze a `.pk3` from URL:

```python
#MAP_PK3 = "yourmap.pk3"
MAP_URL = "https://example.com/yourmap.pk3"
```

Run the script:

```bash
python quake3_map_checker.py
```

## Output

The script will categorize assets as:

* Found in the map PK3
* Found in demo PK3 (`pak0-demo.pk3`)
* Found in point-release patches (`pak1.pk3` - `pak7.pk3`)
* Found only in the full version (`pak0-full.pk3`)

### Verdict

* **YES**: Fully compatible with the demo. The full game is not required.
* **PROBABLY**: Likely playable with demo (≤5 full-only assets). You'll need to determine if they are important or not.
* **NO**: Requires assets exclusively in the full game - the demo version will not suffice.

This helps quickly identify multiplayer maps suitable for demo-version play.

### Contributing

This script was put together fairly quickly and may have bugs or other issues. Feel free to open an issue if you notice anything that can use improving.
