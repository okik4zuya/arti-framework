"""Synthetic panel assets for the arti-compose prototype (no real data)."""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
from scipy.signal import find_peaks
from adjustText import adjust_text
MM = 1 / 25.4
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panels")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "axes.linewidth": 0.5, "svg.fonttype": "none",
                     "axes.spines.top": False, "axes.spines.right": False, "xtick.major.width": 0.5, "ytick.major.width": 0.5})
rng = np.random.default_rng(1)
# (a) XRD-like pattern, vector SVG, text kept as text
tt = np.linspace(10, 70, 1500)
def pat(peaks, noise): 
    y = sum(h * np.exp(-((tt - c) / 0.25) ** 2) for c, h in peaks) + rng.normal(0, noise, tt.size) + 5
    return y
fig, ax = plt.subplots(figsize=(184 * MM, 50.5 * MM))
for k, (lab, pk) in enumerate((("As-synthesised", [(26.5, 100), (33.8, 70), (37.9, 55), (51.7, 40)]), ("Calcined", [(26.6, 160), (33.9, 110), (38.0, 85), (51.8, 60)]))):
    y = pat(pk, 1.2) + k * 190
    ax.plot(tt, y, lw=0.6, color=["#4D4D4D", "#2b6cb0"][k], label=lab)
    if k == 1:
        idx, _ = find_peaks(y, prominence=40)
        txt = [ax.text(tt[i], y[i] + 4, f"{tt[i]:.1f}\u00b0", ha="center", fontsize=7) for i in idx]
        adjust_text(txt, ax=ax)
ax.set_xlabel("2\u03b8 (\u00b0)"); ax.set_ylabel("Intensity (a.u.)"); ax.set_yticks([]); ax.legend(frameon=False, loc="upper right", fontsize=7)
fig.subplots_adjust(left=0.07, right=0.99, bottom=0.24, top=0.97)
fig.savefig(OUT + "/panel_a.svg")
# (b) parity plot, raster PNG at 600 dpi at its display size
x = rng.uniform(0, 10, 40); y = x + rng.normal(0, 0.6, 40)
fig, ax = plt.subplots(figsize=(90.5 * MM, 50.5 * MM))
ax.scatter(x, y, s=8, color="#2b6cb0", lw=0); ax.plot([0, 10], [0, 10], color="#4D4D4D", lw=0.5, ls="--")
ax.set_xlabel("Measured (mg g$^{-1}$)"); ax.set_ylabel("Predicted (mg g$^{-1}$)")
fig.subplots_adjust(left=0.16, right=0.98, bottom=0.26, top=0.97)
fig.savefig(OUT + "/panel_b.png", dpi=600)
# (c) synthetic micrograph-like image (clearly artificial), 600 dpi at display size
w, h = int(90.5 * 600 / 25.4), int(50.5 * 600 / 25.4)
yy, xx = np.mgrid[0:h, 0:w]; img = rng.normal(110, 12, (h, w))
for _ in range(60):
    cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(25, 60)
    img += 70 * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (r / 2) ** 2)))
from PIL import Image, ImageFilter
Image.fromarray(np.clip(img, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.2)).save(OUT + "/panel_c.png", dpi=(600, 600))
print("panels written")
