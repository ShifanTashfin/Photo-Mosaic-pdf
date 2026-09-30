from PIL import Image, ImageOps
import os, random

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    print("Note: pillow-heif not installed, HEIC photos will be skipped.")

FOLDER = r"C:\Users\tashf\Downloads\Journal Pics\Journal"
OUT = r"C:\Users\tashf\Downloads\Journal Pics\journal_photos.pdf"

DPI = 300
COLS, ROWS = 10, 14      # grid of cells per A4 page
PITCH_MM = 20            # size of one cell. Smallest photo = 2 cells
GAP_MM = 2               # white space between photos for cutting
SEED = 1                 # change for a different layout

random.seed(SEED)

def px(mm):
    return int(mm / 25.4 * DPI)

page_w, page_h = px(210), px(297)
pitch, gap = px(PITCH_MM), px(GAP_MM)
x0 = (page_w - (COLS * pitch - gap)) // 2
y0 = (page_h - (ROWS * pitch - gap)) // 2

FALLBACK = [(2, 2), (2, 3), (3, 2), (3, 3), (2, 4), (4, 2)]

def shape_options(aspect):
    if aspect < 0.85:        # portrait
        prefs = [(2, 3), (2, 3), (2, 4), (3, 4)]
    elif aspect > 1.18:      # landscape
        prefs = [(3, 2), (3, 2), (4, 2), (4, 3)]
    else:                    # squarish
        prefs = [(2, 2), (2, 2), (3, 3)]
    random.shuffle(prefs)
    return prefs + FALLBACK

def fits(occ, r, c, w, h):
    if c + w > COLS or r + h > ROWS:
        return False
    return all(not occ[rr][cc] for rr in range(r, r + h) for cc in range(c, c + w))

def place(occ, aspect):
    """Find the first spot where a photo of at least 2x2 cells fits."""
    options = shape_options(aspect)
    for r in range(ROWS):
        for c in range(COLS):
            if occ[r][c]:
                continue
            for w, h in options:
                if fits(occ, r, c, w, h):
                    return r, c, w, h
            occ[r][c] = True    # nothing fits here, leave it blank
    return None

def new_page():
    return Image.new("RGB", (page_w, page_h), "white"), [[False] * COLS for _ in range(ROWS)]

all_files = []
for root, _, names in os.walk(FOLDER):
    for n in sorted(names):
        all_files.append(os.path.join(root, n))

pages, skipped, used = [], [], 0
page, occ = new_page()
on_page = 0

for path in all_files:
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception:
        skipped.append(os.path.basename(path))
        continue

    aspect = img.width / img.height
    spot = place(occ, aspect)
    if spot is None:
        pages.append(page)
        page, occ = new_page()
        on_page = 0
        spot = place(occ, aspect)

    r, c, w, h = spot
    for rr in range(r, r + h):
        for cc in range(c, c + w):
            occ[rr][cc] = True

    tile = ImageOps.fit(img, (w * pitch - gap, h * pitch - gap),
                        Image.LANCZOS, centering=(0.5, 0.4))
    page.paste(tile, (x0 + c * pitch, y0 + r * pitch))
    used += 1
    on_page += 1

if on_page > 0:
    pages.append(page)

pages[0].save(OUT, save_all=True, append_images=pages[1:], resolution=DPI)
print(f"Found {len(all_files)} files, used {used} photos, {len(pages)} pages -> {OUT}")
if skipped:
    print(f"Skipped {len(skipped)} files it couldn't read:")
    for s in skipped[:30]:
        print("  ", s)