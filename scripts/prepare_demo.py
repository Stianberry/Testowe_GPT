from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
assets = ROOT / "examples/quality-demo/assets"
assets.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / "node_modules/gsap/dist/gsap.min.js", assets / "gsap.min.js")
for name in ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]:
    shutil.copy2(Path("/usr/share/fonts/truetype/dejavu") / name, assets / name)
