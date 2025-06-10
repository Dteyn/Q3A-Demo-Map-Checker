# Quake 3 Map Checker - Checks a Quake 3 .pk3 map file to see if it requires the full game or the demo version
# https://github.com/Dteyn/Q3A-Demo-Map-Checker

import zipfile, os, struct, re, sys

# --- CONFIGURE EITHER A LOCAL PATH OR A URL (ONLY ONE) ---
#MAP_PK3   = "tig_den.pk3"     # if you have a local PK3, uncomment this line
MAP_URL     = "https://ws.q3df.org/maps/downloads/tig_den.pk3"

# --- CONFIGURE PATHS ---
DEMO_PAK0    = "baseq3/pak0-demo.pk3"
FULL_PAK0    = "baseq3/pak0-full.pk3"
POINT_PAKS   = [f"baseq3/pak{i}.pk3" for i in range(1, 8)]

# Files to ignore entirely (e.g. common engine-only textures)
IGNORE_PATHS = [
    "textures/common/",
    "textures/radiant/notex",
]

# Terms to ignore entirely
IGNORE_TERMS = {
    "noshader",
    "shadernotfound",
    "$lightmap",
    "$whiteimage",
    "flareshader",
}

# --- Download MAP_URL if MAP_PK3 isn’t defined ---
if not globals().get("MAP_PK3") and MAP_URL:
    import urllib.request
    os.makedirs("downloads", exist_ok=True)
    fname = os.path.basename(MAP_URL)
    MAP_PK3 = os.path.join("downloads", fname)
    print(f"Downloading {MAP_URL} → {MAP_PK3} ...")
    try:
        urllib.request.urlretrieve(MAP_URL, MAP_PK3)
    except Exception as ex:
        print(f"Error downloading: {ex}")
        sys.exit(1)
    print("Download complete.")

def load_zip_list(path):
    if os.path.exists(path):
        with zipfile.ZipFile(path, 'r') as z:
            return {n.lower() for n in z.namelist()}
    return set()

def should_ignore(dep):
    low = dep.lower()
    for pre in IGNORE_PATHS:
        if low.startswith(pre):
            return True
    return False

def find_in_set(base, s):
    """
    Try matching base in set s, checking:
      - base.tga, base.jpg, then base
      - if ends .tga, try .jpg
      - if ends .jpg, try .tga
    """
    low = base.lower()
    cands = []
    name = os.path.basename(low)
    if "." not in name:
        cands = [low + ext for ext in (".tga", ".jpg")] + [low]
    elif low.endswith(".tga"):
        cands = [low, low[:-4] + ".jpg"]
    elif low.endswith(".jpg"):
        cands = [low, low[:-4] + ".tga"]
    else:
        cands = [low]

    for c in cands:
        if c in s:
            return c
    return None

# Load all archives
demo_files  = load_zip_list(DEMO_PAK0)
full_files  = load_zip_list(FULL_PAK0)
patch_files = set()
for p in POINT_PAKS:
    patch_files |= load_zip_list(p)

def gather_deps(pk3_path):
    with zipfile.ZipFile(pk3_path, 'r') as z:
        files = {n.lower() for n in z.namelist()}

        # Find BSP
        bsp_list = [f for f in z.namelist() if f.lower().startswith("maps/") and f.lower().endswith(".bsp")]
        if not bsp_list:
            raise FileNotFoundError("No BSP found in map PK3")
        data = z.read(bsp_list[0])
        if data[:4] != b"IBSP":
            raise ValueError("Invalid BSP")

        # Read lump directory (17 lumps)
        lumps = [struct.unpack("<ii", data[8+i*8:8+i*8+8]) for i in range(17)]

        # Lump 1 = Textures
        off, length = lumps[1]
        count = length // 72
        textures = set()
        for i in range(count):
            name = data[off+i*72:off+i*72+64].split(b"\0",1)[0].decode("ascii", "ignore")
            if name: textures.add(name)

        # Lump 0 = Entities (text)
        off, length = lumps[0]
        ents = data[off:off+length].decode("ascii", "ignore")
        ents_deps = set()
        for key in ("model","model2","noise"):
            for m in re.finditer(rf'"{key}"\s*"([^"]+)"', ents):
                p = m.group(1)
                if p and not p.startswith("*"):
                    ents_deps.add(p)

        # Shader scripts
        shader_deps = set()
        for sfile in [f for f in z.namelist() if f.lower().startswith("scripts/") and f.lower().endswith(".shader")]:
            text = z.read(sfile).decode("utf-8","ignore")
            text = re.sub(r"/\*.*?\*/","",text,flags=re.S)
            text = re.sub(r"//.*","",text)
            for cmd, path in re.findall(r'\b(qer_editorImage|map|clampMap|animMap)\b\s+([^\s]+)', text):
                path = path.strip('"')
                if path.startswith(("textures/","models/","sound/")):
                    shader_deps.add(path)

        return textures | ents_deps | shader_deps, files

def get_texture_folders(map_files):
    # textures/*
    folders = set()
    for f in map_files:
        if f.startswith('textures/'):
            subfolder = f.split('/')
            if len(subfolder) > 1:
                # Only include the immediate subfolders
                folders.add(f'textures/{subfolder[1]}/')
    return folders


# Main
deps, map_files = gather_deps(MAP_PK3)
texture_folders = get_texture_folders(map_files)

found_map, found_demo, found_patch, found_full, missing = [], [], [], [], []
for dep in sorted(deps):
    
    # Skip any any ignored terms
    if dep.lower() in IGNORE_TERMS:
        continue
    
    # Skip items in ignore list
    if should_ignore(dep):
        continue

    # Skip any texture present in the map PK3
    if any(dep.lower().startswith(folder) for folder in texture_folders):
        found_map.append(dep)
        continue

    # Check map pk3 for dependencies
    if find_in_set(dep, map_files):
        found_map.append(dep)
        continue

    # Check demo pak0.pk3 for dependencies
    if find_in_set(dep, demo_files):
        found_demo.append(dep)
        continue

    # Check point patch pk3s for dependencies
    if find_in_set(dep, patch_files):
        found_patch.append(dep)
        continue

    # Check full pak0.pk3s for dependencies
    if find_in_set(dep, full_files):
        found_full.append(dep)
        continue

    # Anything not found, consider it missing
    missing.append(dep)

# Print report - uncomment below for more details as needed
print(f"\nMap: {MAP_PK3}")

# print(f"Found in map PK3:        {len(found_map)}")
# for d in found_map:   print("  ", d)

# print(f"\nFound in demo pak0:      {len(found_demo)}")
# for d in found_demo:  print("  ", d)

# print(f"\nFound in patches pak1-8: {len(found_patch)}")
# for d in found_patch: print("  ", d)

print(f"\nFound only in full pak0: {len(found_full)}")
for d in found_full:  print("  ", d)

# print(f"\nMissing entirely:        {len(missing)}")
# for d in missing:     print("  ", d)

# Count how many dependencies found in the full pak0
count_full = len(found_full)

# Final verdict
if count_full == 0:
    print("\nRESULT: YES — ALL dependencies satisfied by map/demo/patch; playable on demo")
    print(f"\nFound in map PK3:        {len(found_map)}")
    print(f"Found in demo pak0:      {len(found_demo)}")
    print(f"Found in patches pak1-8: {len(found_patch)}")
    print(f"Found ONLY IN FULL pak0: {len(found_full)}")    
    print(f"Missing entirely:        {len(missing)}")
elif count_full <= 5:
    print(f"\nRESULT: PROBABLY — only {count_full} asset(s) require full pak0")
    print(f"\nFound in map PK3:        {len(found_map)}")
    print(f"Found in demo pak0:      {len(found_demo)}")
    print(f"Found in patches pak1-8: {len(found_patch)}")
    print(f"Found ONLY IN FULL pak0: {len(found_full)}")    
    print(f"Missing entirely:        {len(missing)}")
else:
    print(f"\nRESULT: NO — Requires {count_full} assets only in FULL pak0")
    print(f"\nFound ONLY IN FULL pak0: {len(found_full)}")
    print(f"\nFound in map PK3:        {len(found_map)}")
    print(f"Found in demo pak0:      {len(found_demo)}")
    print(f"Found in patches pak1-8: {len(found_patch)}")
    print(f"Missing entirely:        {len(missing)}")
