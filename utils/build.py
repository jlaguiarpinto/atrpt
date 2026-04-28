# build.py
# Corre na raiz do projecto: python build.py [modulo]
#
# Exemplos:
#   python build.py                  → compila aprovisionamento (default)
#   python build.py aprovisionamento → compila aprovisionamento
#   python build.py pessoas          → compila pessoas
#   python build.py ponto            → compila ponto

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent  # build.py está em utils\ — subir para raiz do projecto

MODULOS = {
    "aprovisionamento": {
        "spec":   "aprovisionamento.spec",
        "deploy": Path(r"G:\.shortcut-targets-by-id\1wt9AXRO3Hk4wBQv-tjY_Z8oHn1nR7ful\Servicos_Gerais\Aprovisionamento"),
    },
    "pessoas": {
        "spec":   "pessoas.spec",
        "deploy": Path(r"G:\.shortcut-targets-by-id\1XXDmRuZ3m1vKgqTTG3fUEClqMUFK3jgX\Direcao"),
    },
    "ponto": {
        "spec":   "ponto.spec",
        "deploy": Path(r"G:\.shortcut-targets-by-id\1YUU7cpAVBqQ-XmuiuqVAzKPjw-UZdVg8\CSAG\Ponto"),
    },
}


def run_pyinstaller(spec: str):
    modulo = Path(spec).stem
    print(f"▶ A compilar {spec}...")

    # limpar build anterior para forçar re-análise completa do spec
    for d in (ROOT / "build" / modulo, ROOT / "dist" / modulo):
        if d.exists():
            shutil.rmtree(d)

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", spec],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("✖ PyInstaller falhou.")
        sys.exit(1)
    print("✔ .exe gerado.")


def deploy(modulo: str, deploy_dir: Path):
    exe = ROOT / "dist" / f"{modulo}.exe"
    if not exe.exists():
        print(f"✖ Executável não encontrado: {exe}")
        sys.exit(1)

    print(f"▶ A copiar para {deploy_dir}...")
    deploy_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exe, deploy_dir / exe.name)
    print(f"  ✔ {exe.name}")
    print(f"✔ Deploy concluído em: {deploy_dir}")


if __name__ == "__main__":
    modulo = sys.argv[1] if len(sys.argv) > 1 else "aprovisionamento"

    if modulo not in MODULOS:
        print(f"✖ Módulo desconhecido: '{modulo}'")
        print(f"  Módulos disponíveis: {', '.join(MODULOS)}")
        sys.exit(1)

    cfg = MODULOS[modulo]
    run_pyinstaller(cfg["spec"])
    deploy(modulo, cfg["deploy"])
