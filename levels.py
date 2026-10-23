import math

# (nível mínimo, patente)
PATENTES = [
    (1, "Recruta"),
    (5, "Guerreiro"),
    (10, "Gladiador"),
    (20, "Campeão"),
    (35, "Lenda do Colizeu"),
]


def xp_para_nivel(nivel: int) -> int:
    """XP total necessário para ALCANÇAR o nível."""
    return 100 * (nivel - 1) ** 2


def nivel_por_xp(xp: int) -> int:
    return int(math.sqrt(max(xp, 0) / 100)) + 1


def patente_por_nivel(nivel: int) -> str:
    atual = PATENTES[0][1]
    for minimo, nome in PATENTES:
        if nivel >= minimo:
            atual = nome
    return atual


def barra_progresso(xp: int, tamanho: int = 10) -> str:
    nivel = nivel_por_xp(xp)
    base, topo = xp_para_nivel(nivel), xp_para_nivel(nivel + 1)
    frac = (xp - base) / (topo - base)
    cheio = int(frac * tamanho)
    return "▰" * cheio + "▱" * (tamanho - cheio) + f" {xp - base}/{topo - base} XP"
