"""Genera 04-tarifas.md a partir de las horas de la propuesta y una lista de tarifas por hora.

Uso: python3 docs/presupuesto/calcular_tarifas.py
Cambia HORAS, TARIFAS o los porcentajes y vuelve a ejecutarlo.
"""

from pathlib import Path

TARIFAS = [15, 20, 25, 30, 35, 40]

# Módulos cerrados: (código, nombre, horas mín, horas máx)
CERRADOS = [
    ("F0", "Fase 0: Diagnóstico e inventario", 8, 10),
    ("M1", "Landing y web de noticias", 32, 43),
    ("M2", "Contraseñas", 5, 6),
    ("M3", "Copias de seguridad", 10, 15),
    ("M4", "Lectura y clasificación de correos", 18, 26),
    ("M5", "Redacción con plantilla y aprobación", 22, 31),
    ("M8", "SEO inicial y medición", 10, 12),
    ("M9", "Formación y traspaso", 4, 5),
]

# Bolsas: (código, nombre, horas). Sin contingencia ni gestión: se cobra lo consumido o el paquete.
BOLSAS = [
    ("M6", "Publicación automática (tope de la bolsa)", 24),
    ("M7", "Cuentas e iCloud (paquete de 10 h)", 10),
]

CONTINGENCIA = 0.15   # incluida en el precio de cada módulo cerrado, salvo Fase 0
GESTION = 0.12        # sobre las horas técnicas de los módulos cerrados, salvo Fase 0
SIN_RECARGO = {"F0"}  # módulos cerrados a los que no se aplica contingencia ni gestión

# Mantenimiento: horas equivalentes al mes (soporte incluido + vigilancia y renovaciones)
MANTENIMIENTO = [
    ("Mínimo (web y copias)", "1 h de soporte + 1 h de vigilancia", 2),
    ("Con automatizaciones", "3 h de soporte + 2 h de vigilancia y tokens", 5),
]

NIVELES = {
    "Básico": {"cerrados": ["F0", "M1", "M2", "M3", "M9"], "bolsas": [], "mant": 0},
    "Recomendado": {"cerrados": ["F0", "M1", "M2", "M3", "M9", "M8", "M4", "M5"], "bolsas": [], "mant": 1},
    "Completo": {"cerrados": ["F0", "M1", "M2", "M3", "M9", "M8", "M4", "M5"], "bolsas": ["M6", "M7"], "mant": 1},
}


def r5(x: float) -> int:
    """Redondea a múltiplos de 5 €."""
    return int(round(x / 5.0) * 5)


def precio_cerrado(codigo: str, horas: float, tarifa: float) -> float:
    rec = 0 if codigo in SIN_RECARGO else CONTINGENCIA
    return horas * tarifa * (1 + rec)


def gestion(codigos: list[str], tarifa: float, usar_max: bool) -> float:
    horas = sum((h2 if usar_max else h1) for c, _, h1, h2 in CERRADOS if c in codigos and c not in SIN_RECARGO)
    return horas * tarifa * GESTION


def nivel(nombre: str, tarifa: float) -> tuple[int, int, int]:
    cfg = NIVELES[nombre]
    mn = mx = 0.0
    for c, _, h1, h2 in CERRADOS:
        if c in cfg["cerrados"]:
            mn += precio_cerrado(c, h1, tarifa)
            mx += precio_cerrado(c, h2, tarifa)
    mn += gestion(cfg["cerrados"], tarifa, False)
    mx += gestion(cfg["cerrados"], tarifa, True)
    for c, _, h in BOLSAS:
        if c in cfg["bolsas"]:
            mn += h * tarifa
            mx += h * tarifa
    mens = MANTENIMIENTO[cfg["mant"]][2] * tarifa
    return r5(mn), r5(mx), r5(mens)


def main() -> None:
    out = []
    out.append("# Tarifas: precios por módulo y por nivel\n")
    out.append("Generado con `calcular_tarifas.py` a partir de las horas de `01-propuesta.md`. Importes sin IVA, redondeados a 5 €.\n")
    out.append("## Supuestos\n")
    out.append(f"- Contingencia del {int(CONTINGENCIA*100)} % incluida en el precio de cada módulo cerrado (no en Fase 0 ni en bolsas).")
    out.append(f"- Gestión del proyecto: {int(GESTION*100)} % sobre las horas técnicas de los módulos cerrados (no en Fase 0 ni en bolsas), como línea aparte.")
    out.append("- Bolsas (M6 y M7): horas × tarifa, sin recargos. M6 se factura por lo consumido hasta el tope; M7 por paquete prepagado.")
    for n, d, h in MANTENIMIENTO:
        out.append(f"- Mantenimiento {n.lower()}: {d} = {h} h equivalentes al mes × tarifa.")
    out.append("- Hardware (NAS y discos) y servicios de terceros no están incluidos: van a nombre de la clienta.\n")

    # Resumen por nivel
    out.append("## Resumen por nivel\n")
    out.append("| Tarifa | Básico | Recomendado | Completo | Mantenimiento mínimo | Mantenimiento con automatizaciones |")
    out.append("|---|---|---|---|---|---|")
    for t in TARIFAS:
        b = nivel("Básico", t)
        r = nivel("Recomendado", t)
        c = nivel("Completo", t)
        out.append(f"| **{t} €/h** | {b[0]}–{b[1]} € | {r[0]}–{r[1]} € | {c[0]}–{c[1]} € | {b[2]} €/mes | {r[2]} €/mes |")
    out.append("")
    out.append("Horas totales estimadas (sin gestión): Básico 59–79 h · Recomendado 109–148 h · Completo 143–182 h (M6 contado al tope).\n")

    # Detalle por tarifa
    out.append("## Detalle por módulo\n")
    for t in TARIFAS:
        out.append(f"### Tarifa {t} €/h\n")
        out.append("| Módulo | Horas | Precio |")
        out.append("|---|---|---|")
        for c, nombre, h1, h2 in CERRADOS:
            p1 = r5(precio_cerrado(c, h1, t))
            p2 = r5(precio_cerrado(c, h2, t))
            nota = "" if c in SIN_RECARGO else " (con contingencia)"
            out.append(f"| {c} {nombre} | {h1}–{h2} | {p1}–{p2} €{nota} |")
        for c, nombre, h in BOLSAS:
            out.append(f"| {c} {nombre} | {h} | {r5(h*t)} € |")
        todos = [c for c, *_ in CERRADOS]
        g1 = r5(gestion(todos, t, False))
        g2 = r5(gestion(todos, t, True))
        out.append(f"| Gestión del proyecto (todos los módulos cerrados) | {int(GESTION*100)} % | {g1}–{g2} € |")
        for n, _, h in MANTENIMIENTO:
            out.append(f"| Mantenimiento {n.lower()} | {h} h/mes | {r5(h*t)} €/mes |")
        out.append("")

    Path(__file__).with_name("04-tarifas.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("Escrito 04-tarifas.md")


if __name__ == "__main__":
    main()
