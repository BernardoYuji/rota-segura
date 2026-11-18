import argparse
import csv
import heapq
import math
import os

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

# Dados
LAT0, LON0 = -23.9600, -46.3300     # origem do grid 
PASSO = 0.0014                      # ~150 m entre esquinas
VELOCIDADE_M_MIN = 60               # ~3,6 km/h: ritmo de um idoso caminhando

RUAS_H = ["Rua das Acácias", "Rua dos Ipês", "Av. Beira Rio",
          "Rua das Palmeiras", "Rua do Comércio", "Rua Esperança"]          
RUAS_V = ["Rua das Flores", "Rua do Córrego", "Rua da Escola", "Rua São José",
          "Rua da Paz", "Rua do Sol", "Rua Nova"]                           
LINHAS, COLUNAS = len(RUAS_H), len(RUAS_V)
NOME_CORREGO = "Córrego Boa Esperança"   # corre entre as colunas 1 e 2

# Trechos alagados agora (simulam os sensores)
RUAS_ALAGADAS = [("R1C1", "R1C2"), ("R2C1", "R2C2"), ("R3C1", "R3C2"), ("R1C1", "R2C1")]

# Zona de risco fixa
ZONA_RISCO = {f"R{r}C{c}" for r in range(LINHAS) for c in (1, 2)}

ABRIGOS = {
    "Escola Municipal":    {"no": "R4C5", "status": "aberto", "vagas": 80},
    "Igreja Santa Luzia":  {"no": "R5C0", "status": "aberto", "vagas": 35},
    "Ginásio Comunitário": {"no": "R0C6", "status": "lotado", "vagas": 0},
}

MORADORES = {
    "dona_maria": "Rua do Córrego, 245",
    "seu_joao":   "Rua das Acácias, 520",
    "ana":        "Rua da Escola, 100",
}


def haversine(p1, p2):
    """Distância em metros entre dois pontos (lat, lon)."""
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, (*p1, *p2))
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def nome_esquina(no):
    r, c = int(no[1]), int(no[3])
    return f"{RUAS_V[c]} x {RUAS_H[r]}"


def geocodificar(endereco):
    """'Rua do Córrego, 245' -> nó do grafo (a centena do número indica a esquina)."""
    try:
        rua, numero = endereco.rsplit(",", 1)
        numero = int(numero.strip())
    except ValueError:
        raise ValueError("Use o formato 'Nome da rua, número'. Ex.: Rua do Córrego, 245")
    rua = " ".join(rua.lower().split())
    for r, nome in enumerate(RUAS_H):
        if nome.lower() == rua:
            return f"R{r}C{min(numero // 100, COLUNAS - 1)}"
    for c, nome in enumerate(RUAS_V):
        if nome.lower() == rua:
            return f"R{min(numero // 100, LINHAS - 1)}C{c}"
    raise ValueError(f"Rua não encontrada. Ruas do bairro: {', '.join(RUAS_H + RUAS_V)}")


# GRAFO
class GrafoRuas:
    def __init__(self):
        self.nos = {f"R{r}C{c}": (LAT0 + r * PASSO, LON0 + c * PASSO)
                    for r in range(LINHAS) for c in range(COLUNAS)}
        self.arestas = {}
        for r in range(LINHAS):
            for c in range(COLUNAS):
                if c + 1 < COLUNAS:
                    self.arestas[(f"R{r}C{c}", f"R{r}C{c+1}")] = False
                if r + 1 < LINHAS:
                    self.arestas[(f"R{r}C{c}", f"R{r+1}C{c}")] = False
        self.versao = 0                      # muda quando o alagamento muda
        self.atualizar_alagamentos(RUAS_ALAGADAS)

    def atualizar_alagamentos(self, ruas):
        for k in self.arestas:
            self.arestas[k] = False
        for a, b in ruas:
            self.arestas[(a, b) if (a, b) in self.arestas else (b, a)] = True
        self.versao += 1                     # invalida o cache (memoização)
        self.adj = {n: [] for n in self.nos}
        for (a, b), alagada in self.arestas.items():
            if not alagada:                  # rua alagada não entra na rota
                d = haversine(self.nos[a], self.nos[b])
                self.adj[a].append((b, d))
                self.adj[b].append((a, d))

    def em_risco(self, no):
        """Rota só é necessária na zona de risco do córrego ou se uma rua da esquina alagou."""
        return no in ZONA_RISCO or any(no in t and alagada for t, alagada in self.arestas.items())

    def abrigos_disponiveis(self):
        return {v["no"]: n for n, v in ABRIGOS.items() if v["status"] == "aberto" and v["vagas"] > 0}

    def rota_ao_abrigo_mais_proximo(self, origem):
        """Dijkstra: para no primeiro abrigo disponível retirado da fila (o mais próximo)."""
        destinos = self.abrigos_disponiveis()
        dist, pai, fila = {origem: 0.0}, {}, [(0.0, origem)]
        while fila:
            d, u = heapq.heappop(fila)
            if d > dist.get(u, float("inf")):
                continue
            if u in destinos:
                caminho = [u]
                while caminho[-1] != origem:
                    caminho.append(pai[caminho[-1]])
                return destinos[u], caminho[::-1]
            for v, w in self.adj[u]:
                if d + w < dist.get(v, float("inf")):
                    dist[v], pai[v] = d + w, u
                    heapq.heappush(fila, (d + w, v))
        return None, []


# MEMOIZAÇÃO
class CacheRotas:
    """Guarda por usuário: (usuário, endereço, versão do grafo) -> (abrigo, caminho)."""
    def __init__(self, grafo):
        self.grafo, self.memo, self.hits, self.misses = grafo, {}, 0, 0

    def obter(self, usuario, endereco):
        chave = (usuario, endereco, self.grafo.versao)
        if chave in self.memo:
            self.hits += 1
            return self.memo[chave], True
        self.misses += 1
        self.memo[chave] = self.grafo.rota_ao_abrigo_mais_proximo(geocodificar(endereco))
        return self.memo[chave], False


# TABULAÇÃO
def tabular_rota(grafo, caminho):
    """Tabela bottom-up: cada linha usa o acumulado da anterior."""
    tabela, acumulado = [], 0.0
    for i, no in enumerate(caminho):
        lat, lon = grafo.nos[no]
        trecho = haversine(grafo.nos[caminho[i - 1]], (lat, lon)) if i else 0.0
        acumulado += trecho
        tabela.append({"ordem": i, "no": no, "local": nome_esquina(no),
                       "lat": round(lat, 6), "lon": round(lon, 6),
                       "trecho_m": round(trecho, 1), "acumulado_m": round(acumulado, 1),
                       "tempo_min": round(acumulado / VELOCIDADE_M_MIN, 1)})
    return tabela


def imprimir_tabela(tabela):
    cab = ["ordem", "local", "lat", "lon", "trecho_m", "acumulado_m", "tempo_min"]
    larg = {c: (38 if c == "local" else 11) for c in cab}
    print(" | ".join(f"{c:>{larg[c]}}" for c in cab))
    print("-" * (sum(larg.values()) + 3 * (len(cab) - 1)))
    for l in tabela:
        print(" | ".join(f"{str(l[c]):>{larg[c]}}" for c in cab))


def salvar_csv(tabela, arquivo):
    with open(arquivo, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=tabela[0].keys())
        w.writeheader()
        w.writerows(tabela)


#  MAPA 
def desenhar_mapa(grafo, tabela, abrigo, usuario, endereco):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#dfe9d5")
    xy = lambda no: (grafo.nos[no][1], grafo.nos[no][0]) 

    # córrego sinuoso entre as colunas 1 e 2
    ys = [LAT0 - 0.7 * PASSO + i * (LINHAS - 1 + 1.4) * PASSO / 60 for i in range(61)]
    xs = [LON0 + 1.5 * PASSO + 0.00012 * math.sin((y - LAT0) / PASSO * 1.3) for y in ys]
    ax.plot(xs, ys, color="#8cc8e8", lw=34, solid_capstyle="round", zorder=1)
    ax.plot(xs, ys, color="#6bb3da", lw=24, solid_capstyle="round", zorder=1)
    ax.text(xs[8] - 0.0004, ys[8], NOME_CORREGO, rotation=90, ha="center", va="center",
            fontsize=8, style="italic", color="#1d4560", zorder=2)

    # quadras com casinhas (a faixa do córrego fica livre) e uma praça
    cores = ["#d9a38c", "#c9b38a", "#a9c0d4", "#d8c8a0"]
    m = 0.14 * PASSO
    for r in range(LINHAS - 1):
        for c in range(COLUNAS - 1):
            if c == 1:
                continue
            x0, y0 = LON0 + c * PASSO + m, LAT0 + r * PASSO + m
            w = PASSO - 2 * m
            ax.add_patch(Rectangle((x0, y0), w, w, fc="#ece6d6", ec="none", zorder=2))
            if (r, c) == (2, 4):
                ax.add_patch(Rectangle((x0 + 0.1 * w, y0 + 0.1 * w), 0.8 * w, 0.8 * w, fc="#bcd9a3", ec="none", zorder=2))
                continue
            for i in range(4):
                for j in range(2):
                    ax.add_patch(Rectangle((x0 + 0.08 * w + i * 0.22 * w, y0 + 0.1 * w + j * 0.55 * w),
                                           0.17 * w, 0.28 * w, fc=cores[(r + c + i + j) % 4],
                                           ec="#8a7a60", lw=0.4, zorder=3))

    # ruas (cinza + branco); trechos alagados em vermelho tracejado
    for (a, b), alagada in grafo.arestas.items():
        (x1, y1), (x2, y2) = xy(a), xy(b)
        ax.plot([x1, x2], [y1, y2], color="#b0b0b0", lw=9, solid_capstyle="round", zorder=4)
        ax.plot([x1, x2], [y1, y2], color="white", lw=6.5, solid_capstyle="round", zorder=4)
        if alagada:
            ax.plot([x1, x2], [y1, y2], color="#d32f2f", lw=4, ls=(0, (2, 1.5)), zorder=5)

    # nomes das ruas
    for r, nome in enumerate(RUAS_H):
        ax.text(LON0 - 0.15 * PASSO, LAT0 + r * PASSO, nome, ha="right", va="center", fontsize=8, zorder=8)
    for c, nome in enumerate(RUAS_V):
        ax.text(LON0 + c * PASSO, LAT0 + (LINHAS - 1) * PASSO + 0.18 * PASSO, nome,
                rotation=35, ha="left", va="bottom", fontsize=8, zorder=8)

    # rota segura
    lons, lats = [xy(l["no"])[0] for l in tabela], [xy(l["no"])[1] for l in tabela]
    ax.plot(lons, lats, color="#1a73e8", lw=5, solid_capstyle="round", solid_joinstyle="round", zorder=6)
    for l, x, y in zip(tabela, lons, lats):
        ax.text(x, y, str(l["ordem"]), ha="center", va="center", fontsize=7, color="white", zorder=9,
                bbox=dict(boxstyle="circle,pad=0.25", fc="#1a73e8", ec="white"))

    # abrigos
    for nome, v in ABRIGOS.items():
        x, y = xy(v["no"])
        cor = "#2e7d32" if v["status"] == "aberto" else "#757575"
        ax.text(x, y, "A", ha="center", va="center", fontsize=11, fontweight="bold", color="white", zorder=10,
                bbox=dict(boxstyle="round,pad=0.35", fc=cor, ec="white", lw=1.5))
        topo = v["no"].startswith(f"R{LINHAS-1}")          # abrigo na borda norte: rótulo vai embaixo
        ax.text(x, y + (-0.28 if topo else 0.28) * PASSO, f"{nome}\n({v['status']})", ha="center",
                va="top" if topo else "bottom", fontsize=8,
                fontweight="bold", zorder=10, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

    # casa do morador
    x, y = lons[0], lats[0]
    ax.plot(x, y, marker="p", ms=20, mfc="white", mec="#1a73e8", mew=3, zorder=10)
    ax.text(x, y - 0.3 * PASSO, "Sua casa", ha="center", va="top", fontsize=9, fontweight="bold", zorder=10,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))

    ax.set_xlim(LON0 - 1.6 * PASSO, LON0 + (COLUNAS - 1) * PASSO + 0.6 * PASSO)
    ax.set_ylim(LAT0 - 0.7 * PASSO, LAT0 + (LINHAS - 1) * PASSO + 1.1 * PASSO)
    ax.set_aspect(1 / math.cos(math.radians(LAT0)))
    ax.axis("off")
    fig.subplots_adjust(top=0.88, bottom=0.1)
    resumo = f"{tabela[-1]['acumulado_m']:.0f} m ≈ {tabela[-1]['tempo_min']:.0f} min a pé"
    fig.suptitle(f"Rota Segura – {usuario} · {endereco}", fontsize=14, fontweight="bold", color="#1b5e20")
    ax.set_title(f"Trajeto seguro encontrado! Destino: {abrigo} · {resumo}", fontsize=11)
    ax.legend(handles=[Line2D([0], [0], color="#1a73e8", lw=4, label="Rota segura"),
                       Line2D([0], [0], color="#d32f2f", lw=3, ls="--", label="Trecho alagado"),
                       Line2D([0], [0], marker="s", color="w", mfc="#2e7d32", ms=10, label="Abrigo aberto"),
                       Line2D([0], [0], marker="s", color="w", mfc="#757575", ms=10, label="Abrigo lotado")],
              loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=4, fontsize=9, frameon=False)
    fig.text(0.5, 0.02, "Bairro fictício para simulação. Dados não reais.", ha="center", fontsize=8, color="#666")
    return fig


# MAIN
def processar(cache, grafo, usuario, endereco, figuras, salvar):
    try:
        origem = geocodificar(endereco)
    except ValueError as e:
        print(f"\nEndereço inválido ({endereco}): {e}")
        return
    print(f"\n=== {usuario} | {endereco} ===")
    if not grafo.em_risco(origem):
        print("Rua sem risco de alagamento: rota de fuga não necessária.")
        return
    (abrigo, caminho), do_cache = cache.obter(usuario, endereco)
    print("Origem do resultado:", "CACHE (memoização)" if do_cache else "calculado (Dijkstra)")
    if not caminho:
        print("Nenhum abrigo alcançável por rota segura!")
        return
    print(f"Abrigo mais próximo: {abrigo}")
    tabela = tabular_rota(grafo, caminho)
    imprimir_tabela(tabela)
    if do_cache:
        print("(rota vinda do cache: o mapa deste morador já foi aberto)")
        return
    salvar_csv(tabela, f"rota_{usuario}.csv")
    fig = desenhar_mapa(grafo, tabela, abrigo, usuario, endereco)
    if salvar:
        fig.savefig(f"mapa_{usuario}.png", dpi=150, bbox_inches="tight")
        print(f"Imagem salva: mapa_{usuario}.png")
    figuras.append(fig)


def main():
    ap = argparse.ArgumentParser(description="Rota Segura - bairro fictício Vila Esperança")
    ap.add_argument("--endereco", help='Ex.: "Rua do Córrego, 245"')
    ap.add_argument("--usuario", default="visitante")
    ap.add_argument("--salvar", action="store_true", help="grava os mapas também em PNG")
    args = ap.parse_args()

    grafo, figuras = GrafoRuas(), []
    cache = CacheRotas(grafo)

    if args.endereco:
        processar(cache, grafo, args.usuario, args.endereco, figuras, args.salvar)
    else:
        for usuario, endereco in list(MORADORES.items()) + [("dona_maria", MORADORES["dona_maria"])]:
            processar(cache, grafo, usuario, endereco, figuras, args.salvar)
        print(f"\nCache: {cache.hits} acertos / {cache.misses} cálculos")

        # Sensor detecta mais alagamento -> versão do grafo muda -> cache invalidado
        grafo.atualizar_alagamentos(RUAS_ALAGADAS + [("R3C2", "R4C2")])
        (abrigo, _), do_cache = cache.obter("dona_maria", MORADORES["dona_maria"])
        print(f"Após novo alagamento: recalculado={not do_cache}, abrigo={abrigo}")

    if figuras:
        plt.show()       


if __name__ == "__main__":
    main()