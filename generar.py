#!/usr/bin/env python3
"""Genera las variantes Solarized para KDE Plasma 6.

  Esquemas de color:  ~/.local/share/color-schemes/Solarized{Light,Dark}{Gris,Cian,Amarillo}.colors
  Plasma Style:       ~/.local/share/plasma/desktoptheme/darkly-solarized[-cian|-amarillo]
  Íconos:             ~/.local/share/icons/breeze-solarized             (íconos de bandeja)
                      ~/.local/share/icons/breeze-solarized-{amarillo,azul,gris}  (carpetas)

Uso:  python3 generar.py            # instala/actualiza todo
      python3 generar.py --quitar   # borra todo lo generado
"""
import glob, json, os, re, shutil, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"))
SCHEMES = f"{DATA}/color-schemes"
STYLES = f"{DATA}/plasma/desktoptheme"
ICONS = f"{DATA}/icons"

# --- Personalización ---------------------------------------------------------
BASE03, BASE3 = "0,43,54", "253,246,227"
# nombre: {variante: (acento, fondo de la selección, texto seleccionado)}
# El texto seleccionado debe leerse también sobre el fondo de la vista: con el estilo
# Darkly, Dolphin resalta solo el ícono y el nombre queda fuera del resaltado.
# Por eso: texto oscuro en Light, texto crema en Dark, y fondos que contrasten con él.
ACENTOS = {
    "Gris": {"Light": ("101,123,131", "147,161,161", BASE03),
             "Dark": ("101,123,131", "101,123,131", BASE3)},
    "Cian": {"Light": ("42,161,152", "42,161,152", BASE03),
             "Dark": ("33,126,119", "33,126,119", BASE3)},
    "Amarillo": {"Light": ("181,137,0", "181,137,0", BASE03),
                 "Dark": ("143,108,0", "143,108,0", BASE3)},
}
CARPETAS = {"amarillo": "#b58900", "azul": "#268bd2", "gris": "#657b83"}
# ------------------------------------------------------------------------------

AZUL_ORIGINAL = "38,139,210"  # acento de los esquemas de ret2src
STYLE_SVG = ('<style type="text/css" id="current-color-scheme">'
             '.ColorScheme-Text { color:#232629; }</style>')


def buscar(*rutas):
    for r in rutas:
        r = os.path.expanduser(r)
        if os.path.exists(r):
            return r
    return None


def recolorear(texto, acento, fondo_sel, texto_sel):
    texto = texto.replace(AZUL_ORIGINAL, acento)

    def seleccion(m):
        b = m.group(0)
        for clave, valor in (("BackgroundNormal", fondo_sel), ("ForegroundNormal", texto_sel),
                             ("ForegroundActive", texto_sel)):
            b = re.sub(rf"^{clave}=.*$", f"{clave}={valor}", b, flags=re.M)
        return b

    return re.sub(r"^\[Colors:Selection\]\n(?:(?!\[).*\n)*", seleccion, texto, flags=re.M)


def esquemas():
    os.makedirs(SCHEMES, exist_ok=True)
    for variante in ("Light", "Dark"):
        base = open(f"{AQUI}/schemes/BreezeSolarized{variante}.colors").read()
        for nombre, variantes in ACENTOS.items():
            out = recolorear(base, *variantes[variante])
            out = re.sub(r"^Name=.*$", f"Name=Solarized {variante} · {nombre}", out, count=1, flags=re.M)
            open(f"{SCHEMES}/Solarized{variante}{nombre}.colors", "w").write(out)
    print(f"✓ esquemas de color: {len(ACENTOS) * 2}")


def estilos_plasma():
    darkly = buscar(f"{STYLES}/darkly", "/usr/share/plasma/desktoptheme/darkly")
    if not darkly:
        print("· Plasma Style Darkly no encontrado: se omiten los estilos del panel")
        return
    oscuro = open(f"{AQUI}/schemes/BreezeSolarizedDark.colors").read()
    for nombre, variantes in ACENTOS.items():
        sid = "darkly-solarized" if nombre == "Gris" else f"darkly-solarized-{nombre.lower()}"
        dst = f"{STYLES}/{sid}"
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(darkly, dst, symlinks=True)
        open(f"{dst}/colors", "w").write(recolorear(oscuro, *variantes["Dark"]))
        meta = json.load(open(f"{dst}/metadata.json"))
        k = meta["KPlugin"]
        k["Id"], k["Name"] = sid, f"Darkly Solarized · {nombre}"
        for clave in [c for c in k if c.startswith(("Name[", "Description["))]:
            del k[clave]
        json.dump(meta, open(f"{dst}/metadata.json", "w"), indent=4, ensure_ascii=False)
    print(f"✓ Plasma Styles: {len(ACENTOS)} (desde {darkly})")


def iconos_bandeja(apps):
    os.makedirs(apps, exist_ok=True)
    hechos = []
    # Proton VPN: silueta monocroma; la insignia de estado conserva su color
    origen = buscar("/var/lib/flatpak/exports/share/icons/hicolor/scalable/apps",
                    "~/.local/share/flatpak/exports/share/icons/hicolor/scalable/apps")
    insignia = {"state-connected": "#859900", "state-error": "#dc322f"}
    for nombre in ["state-connected", "state-disconnected", "state-error", "maintenance-icon"]:
        fn = f"com.protonvpn.www.{nombre}.svg"
        src = origen and os.path.join(origen, fn)
        if not src or not os.path.exists(src):
            continue
        svg = open(os.path.realpath(src)).read()
        vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
        paths = re.findall(r"<path\b[^>]*>", svg, re.S)
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">', STYLE_SVG]
        for i, p in enumerate(paths):
            d = re.search(r'\sd="([^"]+)"', p).group(1)
            attrs = f'd="{d}"' + (' fill-rule="evenodd"' if "evenodd" in p or nombre == "maintenance-icon" else "")
            if nombre in insignia and i == len(paths) - 1:
                out.append(f'<path {attrs} fill="{insignia[nombre]}"/>')
            else:
                out.append(f'<path {attrs} class="ColorScheme-Text" fill="currentColor"/>')
        open(os.path.join(apps, fn), "w").write("\n".join(out + ["</svg>"]))

    if origen and any(os.path.exists(os.path.join(apps, f"com.protonvpn.www.{n}.svg"))
                      for n in insignia):
        hechos.append("Proton VPN")

    # SyncThingy: logo de Syncthing dibujado a mano, monocromo
    cx, cy = 8.6, 8.4
    nodos = [(12.6, 3.6), (13.4, 11.4), (2.5, 9.6)]
    lineas = "".join(f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="currentColor" '
                     f'stroke-width="1.1" class="ColorScheme-Text"/>' for x, y in nodos)
    puntos = "".join(f'<circle cx="{x}" cy="{y}" r="1.5" fill="currentColor" class="ColorScheme-Text"/>'
                     for x, y in nodos)
    open(os.path.join(apps, "com.github.zocker_160.SyncThingy.white.svg"), "w").write(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">' + STYLE_SVG +
        '<circle cx="8" cy="8" r="6.4" fill="none" stroke="currentColor" stroke-width="1.2" '
        'class="ColorScheme-Text"/>' + lineas + puntos +
        f'<circle cx="{cx}" cy="{cy}" r="1.6" fill="currentColor" class="ColorScheme-Text"/></svg>')
    hechos.append("SyncThingy")
    return hechos


def iconos():
    breeze = buscar("/usr/share/icons/breeze")
    if not breeze:
        print("· Tema de íconos Breeze no encontrado: se omiten los íconos")
        return
    # tema base: íconos de bandeja; las carpetas siguen el acento
    base = f"{ICONS}/breeze-solarized"
    shutil.rmtree(base, ignore_errors=True)
    hechos = iconos_bandeja(f"{base}/scalable/apps")
    open(f"{base}/index.theme", "w").write(
        "[Icon Theme]\nName=Breeze Solarized · Carpetas según acento\n"
        "Comment=Breeze con ajustes para la paleta Solarized\n"
        # FollowsColorScheme: sin esto Plasma no recolorea los íconos y quedan oscuros sobre el panel
        "Inherits=breeze,hicolor\nFollowsColorScheme=true\nDirectories=scalable/apps\n\n"
        "[scalable/apps]\nSize=32\nMinSize=8\nMaxSize=512\nType=Scalable\nContext=Applications\n")

    # variantes con carpetas de color fijo
    indice = open(f"{breeze}/index.theme").read()
    secciones = re.findall(r"^\[(places/[^\]]+)\]\n((?:(?!\[).*\n)*)", indice, flags=re.M)
    elemento = re.compile(r"<[a-zA-Z]+\b[^>]*ColorScheme-Accent[^>]*>", re.S)
    src_places = f"{breeze}/places"
    for nombre, hexc in CARPETAS.items():
        dst = f"{ICONS}/breeze-solarized-{nombre}"
        shutil.rmtree(dst, ignore_errors=True)
        for raiz, _, archivos in os.walk(src_places):
            rel = os.path.relpath(raiz, src_places)
            os.makedirs(f"{dst}/places/{rel}", exist_ok=True)
            for fn in archivos:
                s, d = os.path.join(raiz, fn), f"{dst}/places/{rel}/{fn}"
                if os.path.islink(s):
                    os.symlink(os.readlink(s), d)
                    continue
                svg = open(s).read()
                if "ColorScheme-Accent" not in svg:
                    continue  # sin acento: se hereda de breeze
                svg = elemento.sub(lambda m: re.sub(r'\s*class="ColorScheme-Accent"', "",
                                                    m.group(0).replace("currentColor", hexc)), svg)
                open(d, "w").write(svg)
        # enlaces a archivos que no copiamos: se heredan de breeze
        for p in glob.glob(f"{dst}/places/**/*", recursive=True):
            if os.path.islink(p) and not os.path.exists(p):
                os.remove(p)
        dirs = ",".join(s for s, _ in secciones)
        cuerpo = "".join(f"[{s}]\n{b}\n" for s, b in secciones)
        open(f"{dst}/index.theme", "w").write(
            f"[Icon Theme]\nName=Breeze Solarized · Carpetas {nombre}\n"
            f"Comment=Breeze Solarized con carpetas {hexc}\n"
            "Inherits=breeze-solarized,breeze,hicolor\nFollowsColorScheme=true\n"
            f"Directories={dirs}\n\n{cuerpo}")
    print(f"✓ temas de íconos: {len(CARPETAS) + 1} (bandeja: {', '.join(hechos)})")


def quitar():
    rutas = (glob.glob(f"{SCHEMES}/Solarized*.colors")
             + glob.glob(f"{STYLES}/darkly-solarized*")
             + glob.glob(f"{ICONS}/breeze-solarized*"))
    for r in rutas:
        shutil.rmtree(r) if os.path.isdir(r) else os.remove(r)
        print(f"borrado {r}")
    print("Recuerda volver a aplicar otro esquema, Plasma Style y tema de íconos.")


if __name__ == "__main__":
    if "--quitar" in sys.argv:
        quitar()
    else:
        esquemas()
        estilos_plasma()
        iconos()
        print("\nAplica una combinación desde Configuración del sistema o con:\n"
              "  plasma-apply-colorscheme SolarizedLightGris\n"
              "  plasma-apply-desktoptheme darkly-solarized\n"
              "  /usr/libexec/plasma-changeicons breeze-solarized-amarillo")
