import base64
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

FONTS_DIR = BASE_DIR / "farmacia" / "static" / "farmacia" / "fonts"
OUT_JS = BASE_DIR / "farmacia" / "static" / "farmacia" / "fonts" / "dejavu_vfs.js"

def b64file(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")

def main():
    regular = FONTS_DIR / "DejaVuSans.ttf"
    bold = FONTS_DIR / "DejaVuSans-Bold.ttf"

    if not regular.exists():
        raise SystemExit(f"No existe: {regular}")
    if not bold.exists():
        raise SystemExit(f"No existe: {bold}")

    js = []
    js.append("// Auto-generado. No editar a mano.\n")
    js.append(f"window.DEJAVU_SANS_TTF_BASE64 = '{b64file(regular)}';\n")
    js.append(f"window.DEJAVU_SANS_BOLD_TTF_BASE64 = '{b64file(bold)}';\n")

    OUT_JS.write_text("".join(js), encoding="utf-8")
    print(f"OK: {OUT_JS}")

if __name__ == "__main__":
    main()
