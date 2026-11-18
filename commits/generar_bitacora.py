"""
Genera la bitácora de commits del repositorio en la carpeta commits/.

Crea un archivo Markdown por commit (NNN_<hash>.md) con hash, autor,
fecha, mensaje y archivos modificados, más un índice en README.md.
Los commits que solo cambian la carpeta commits/ se omiten.

Uso (desde la raíz del repositorio):
    python commits/generar_bitacora.py
"""

import subprocess
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parent
SEP = "\x1f"
ESTADOS = {"A": "Agregado", "M": "Modificado", "D": "Eliminado", "R": "Renombrado", "C": "Copiado", "T": "Tipo cambiado"}


def git(*args):
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", check=True).stdout


def commits():
    salida = git("log", "--reverse", f"--format=%H{SEP}%h{SEP}%an{SEP}%ad{SEP}%s", "--date=format:%Y-%m-%d %H:%M")
    for linea in salida.splitlines():
        completo, corto, autor, fecha, asunto = linea.split(SEP)
        yield {"hash": completo, "corto": corto, "autor": autor, "fecha": fecha, "asunto": asunto}


def archivos(hash_):
    filas = []
    for linea in git("show", "--format=", "--name-status", "-M", hash_).splitlines():
        partes = linea.split("\t")
        estado = ESTADOS.get(partes[0][0], partes[0])
        ruta = " → ".join(partes[1:])
        filas.append((estado, ruta))
    return filas


def main():
    for viejo in CARPETA.glob("[0-9][0-9][0-9]_*.md"):
        viejo.unlink()

    indice = []
    numero = 0

    for c in commits():
        cambios = archivos(c["hash"])
        if cambios and all(r.startswith("commits/") for _, r in cambios):
            continue

        numero += 1
        cuerpo = git("show", "-s", "--format=%b", c["hash"]).strip()
        cuerpo = "\n".join(l for l in cuerpo.splitlines() if not l.startswith(("Co-Authored-By:", "Claude-Session:"))).strip()
        stat = git("show", "--format=", "--shortstat", c["hash"]).strip()

        nombre = f"{numero:03d}_{c['corto']}.md"
        lineas = [
            f"# {numero:03d} · {c['asunto']}",
            "",
            "| Campo | Valor |",
            "|---|---|",
            f"| Hash | `{c['hash']}` |",
            f"| Autor | {c['autor']} |",
            f"| Fecha | {c['fecha']} |",
            f"| Cambios | {stat or '—'} |",
            "",
        ]
        if cuerpo:
            lineas += ["## Descripción", "", cuerpo, ""]
        lineas += ["## Archivos", "", "| Estado | Archivo |", "|---|---|"]
        lineas += [f"| {e} | `{r}` |" for e, r in cambios] or ["| — | — |"]

        (CARPETA / nombre).write_text("\n".join(lineas) + "\n", encoding="utf-8")
        indice.append(f"| {numero:03d} | [`{c['corto']}`]({nombre}) | {c['fecha']} | {c['autor']} | {c['asunto']} |")

    readme = [
        "# Bitácora de commits",
        "",
        "Historial del proyecto ElectroMarket, un archivo por commit.",
        "Para actualizarla después de nuevos commits ejecuta desde la raíz:",
        "",
        "```",
        "python commits/generar_bitacora.py",
        "```",
        "",
        "| # | Commit | Fecha | Autor | Mensaje |",
        "|---|---|---|---|---|",
        *indice,
        "",
    ]
    (CARPETA / "README.md").write_text("\n".join(readme), encoding="utf-8")
    print(f"Bitácora generada: {numero} commits.")


if __name__ == "__main__":
    main()
