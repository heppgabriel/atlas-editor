"""Chat do editor: o usuário pede uma alteração em português ("põe um letreiro em cada dia que ele fala: 7, 14, 30") e o
Claude devolve a resposta e a lista de OPERAÇÕES sobre o plano da versão aberta. Quem aplica é o editor (a página), em
cima do plano que está na tela: entra no Desfazer como qualquer mexida e só vai para o disco quando o usuário salvar.

O Claude recebe a fala com o tempo de cada palavra (das legendas), os letreiros, os B-rolls e os efeitos que já existem,
os estilos de letreiro do template e as regras dele. Cobra pela chave da API ou pela assinatura, como o resto do Atlas,
e o custo entra no projeto (aba Custo)."""
import os, json, math

import ia, custos
from ia import texto

OPS = ("add_letreiro", "editar_letreiro", "apagar_letreiro", "apagar_broll", "ajustar_broll",
       "add_efeito", "apagar_efeito", "legenda")
EFEITOS = ("escuro", "pb", "flash", "glitch")
TIPOS_BROLL = ("cheia", "canto", "dividida", "card")
MAX_HIST = 12                     # mensagens anteriores que voltam para o Claude (o resto da conversa fica só na tela)

SISTEMA = """Você é o assistente do editor de vídeo do Atlas: o editor está aberto num anúncio vertical (fala de uma pessoa,
com B-rolls por cima, letreiros, legenda e efeitos) e o usuário pede alterações em português, conversando. Você responde
em português, curto, e devolve as OPERAÇÕES que fazem a alteração no plano. Quem aplica é o editor, na hora, e o usuário
pode desfazer — então faça o que foi pedido, sem pedir confirmação, a menos que o pedido seja ambíguo de verdade (aí
pergunte em `resposta` e devolva `operacoes` vazia).

Como as coisas funcionam:
- Tempos em segundos do vídeo final. A fala vem com o tempo de cada palavra: use esses tempos para casar o letreiro com o
  momento em que a palavra é dita (o letreiro entra junto ou um pouco antes da palavra-chave, nunca depois).
- Letreiro = bloco de 1 a 3 linhas. Cada linha tem um `estilo` (os do template, abaixo), o `texto` e o tempo `t` em que ela
  entra; as linhas entram em sequência (t crescente) e o bloco todo sai em `fim`. `topo` é a altura da primeira linha
  (0 = topo da tela, 1 = base); -1 usa a altura padrão do template. Números ficam bem no estilo de número; uma palavra
  pequena de apoio ("DIA", "SEMANA") fica bem no estilo branco pequeno, numa linha antes do número.
- Respeite as regras do template (palavras e linhas por letreiro, duração máxima, letreiro em cima de B-roll etc.).
  Se a alteração pedida quebrar uma regra, faça mesmo assim e avise em `resposta`.
- Não crie letreiro que se sobreponha a outro: se já existe um letreiro no mesmo momento, edite-o ou apague-o.
- Índices (`i`) são os das listas que você recebe AGORA (letreiro i, B-roll i, efeito i, legenda i). Várias operações no
  mesmo pedido usam os índices originais: o editor aplica apagamentos por último.
- Campos que a operação não usa: i = -1, linhas = [], ini = -1, fim = -1, topo = -1, tipo = "", ocultar = false.

Operações:
- add_letreiro: linhas, fim, topo
- editar_letreiro: i; linhas (vazia = mantém), fim (-1 = mantém), topo (-1 = mantém)
- apagar_letreiro: i
- apagar_broll: i
- ajustar_broll: i; ini e fim (-1 = mantém); tipo = cheia, canto, dividida ou card ("" = mantém)
- add_efeito: tipo = escuro, pb, flash ou glitch; ini; fim (flash só usa ini; glitch dura de ini a fim)
- apagar_efeito: tipo; i (índice na lista desse efeito)
- legenda: i; ocultar = true esconde aquela legenda, false volta a mostrar

`resposta`: o que você fez, em 1 a 3 frases (diga os tempos, ex.: "Coloquei 3 letreiros: DIA 7 em 0:42, DIA 14 em 1:10…").
Se não achou na fala o que o usuário citou, diga isso."""

def num(x, casas=2):
    try:
        v = float(x); return round(v, casas) if math.isfinite(v) else None
    except (TypeError, ValueError): return None

def mmss(t):
    t = max(0.0, float(t or 0)); return f"{int(t // 60)}:{t % 60:05.2f}"

def fala(P):
    """A fala, uma legenda por linha, com o tempo de cada palavra quando a legenda tem (pals)."""
    out = []
    for i, lg in enumerate(P.get("legendas") or []):
        pals = lg.get("pals") if isinstance(lg.get("pals"), list) else None
        oc = " (oculta)" if lg.get("oculto") else ""
        if pals:
            ws = " ".join(f"{w}@{num(a)}" for w, a, *_ in pals if isinstance(w, str))
            out.append(f"legenda {i} [{num(lg.get('ini'))}–{num(lg.get('fim'))}]{oc}: {ws}")
        else:
            out.append(f"legenda {i} [{num(lg.get('ini'))}–{num(lg.get('fim'))}]{oc}: {lg.get('txt', '')}")
    return "\n".join(out) or "(sem legendas nesta versão)"

def letreiros(P):
    out = []
    for i, b in enumerate(P.get("blocos") or []):
        ls = b.get("linhas") or []
        ini = min((num(l[2]) or 0 for l in ls), default=0)
        txt = " | ".join(f"{l[0]}:{l[1]}@{num(l[2])}" for l in ls)
        out.append(f"letreiro {i} [{ini}–{num(b.get('fim'))}] topo {num(b.get('topo'), 3)}: {txt}")
    return "\n".join(out) or "(nenhum)"

def brolls(P):
    out = [f"B-roll {i} [{num(c.get('ini'))}–{num(c.get('fim'))}] {c.get('tipo', 'cheia')} · {c.get('id') or os.path.basename(str(c.get('src', '')))}"
           for i, c in enumerate(P.get("cenas") or [])]
    return "\n".join(out) or "(nenhum)"

def efeitos(P):
    out = []
    for i, (a, b) in enumerate(P.get("escuro") or []): out.append(f"escuro {i} [{num(a)}–{num(b)}]")
    for i, (a, b) in enumerate(P.get("pb") or []): out.append(f"pb {i} [{num(a)}–{num(b)}]")
    for i, t in enumerate(P.get("flash") or []): out.append(f"flash {i} em {num(t)}")
    for i, (a, d) in enumerate(P.get("glitch") or []): out.append(f"glitch {i} [{num(a)}–{num((a or 0) + (d or 0))}]")
    return "\n".join(out) or "(nenhum)"

def contexto(P, E, agora=None):
    est = (E.get("letreiro") or {}).get("estilos") or {}
    estilos = "\n".join(f"- {k}: {v.get('rotulo', k)}" for k, v in est.items()) or "- sans"
    regras = json.dumps(E.get("regras") or {}, ensure_ascii=False)
    return (f"# Vídeo\nduração {num(P.get('dur'))} s · cursor do editor em {num(agora) if agora is not None else '?'} s\n"
            f"template: {E.get('nome', '')} — {E.get('descricao', '')[:300]}\n"
            f"altura padrão do letreiro (topo): {(E.get('letreiro') or {}).get('topo_padrao', 0.12)}\n\n"
            f"# Estilos de letreiro do template\n{estilos}\n\n# Regras do template\n{regras}\n\n"
            f"# Fala (palavra@segundo)\n{fala(P)}\n\n# Letreiros\n{letreiros(P)}\n\n# B-rolls\n{brolls(P)}\n\n# Efeitos\n{efeitos(P)}")

def schema(estilos):
    S = lambda: {"type": "string"}; N = lambda: {"type": "number"}
    obj = lambda **p: {"type": "object", "additionalProperties": False, "required": list(p), "properties": p}
    linha = obj(estilo={"type": "string", "enum": list(estilos) or ["sans"]}, texto=S(), t=N())
    op = obj(op={"type": "string", "enum": list(OPS)}, i={"type": "integer"}, linhas={"type": "array", "items": linha},
             ini=N(), fim=N(), topo=N(), tipo={"type": "string", "enum": ["", *EFEITOS, *TIPOS_BROLL]}, ocultar={"type": "boolean"})
    return obj(resposta=S(), operacoes={"type": "array", "items": op})

def limpar(r, P, estilos):
    """Confere o que veio: índice que existe, tempo dentro do vídeo, estilo do template. O que não passa é descartado
    e contado em `descartadas`, para a tela avisar."""
    dur = float(P.get("dur") or 0); ok, fora = [], 0
    tam = dict(letreiro=len(P.get("blocos") or []), broll=len(P.get("cenas") or []), legenda=len(P.get("legendas") or []))
    tempo = lambda t: t is None or t < 0 or (0 <= t <= dur + 0.01)
    for o in r.get("operacoes") or []:
        op, i = o.get("op"), o.get("i", -1)
        linhas = [dict(estilo=l["estilo"], texto=str(l.get("texto") or "").strip()[:80], t=round(float(l.get("t") or 0), 2))
                  for l in o.get("linhas") or [] if l.get("estilo") in estilos and str(l.get("texto") or "").strip()]
        linhas.sort(key=lambda l: l["t"])
        ini, fim, topo = num(o.get("ini")), num(o.get("fim")), num(o.get("topo"), 3)
        valido = op in OPS and tempo(ini) and tempo(fim) and all(0 <= l["t"] <= dur for l in linhas)
        if op == "add_letreiro": valido = valido and bool(linhas) and fim is not None and fim > linhas[-1]["t"]
        if op in ("editar_letreiro", "apagar_letreiro"): valido = valido and 0 <= i < tam["letreiro"]
        if op in ("apagar_broll", "ajustar_broll"): valido = valido and 0 <= i < tam["broll"]
        if op == "ajustar_broll": valido = valido and o.get("tipo") in ("", *TIPOS_BROLL)
        if op == "legenda": valido = valido and 0 <= i < tam["legenda"]
        if op == "add_efeito": valido = valido and o.get("tipo") in EFEITOS and ini is not None and ini >= 0
        if op == "apagar_efeito": valido = valido and o.get("tipo") in EFEITOS and 0 <= i < len(P.get(o["tipo"]) or [])
        if not valido: fora += 1; continue
        ok.append(dict(op=op, i=i, linhas=linhas, ini=ini if ini is not None else -1, fim=fim if fim is not None else -1,
                       topo=topo if topo is not None else -1, tipo=o.get("tipo") or "", ocultar=bool(o.get("ocultar"))))
    return dict(resposta=str(r.get("resposta") or "").strip(), operacoes=ok, descartadas=fora)

def responder(proj, P, E, mensagem, historico=(), agora=None, log=lambda *_: None):
    estilos = list(((E.get("letreiro") or {}).get("estilos") or {"sans": {}}).keys())
    def cobra(info):
        try: custos.registrar(proj, servico="claude", etapa="chat do editor", fonte="tokens informados pela API × preço de tabela", **info)
        except Exception: pass
    cl = ia.Claude(log=log, ao_cobrar=cobra)
    hist = "\n".join(f"{'Usuário' if h.get('quem') == 'eu' else 'Você'}: {str(h.get('txt', ''))[:600]}" for h in list(historico)[-MAX_HIST:])
    partes = [texto(contexto(P, E, agora))]
    if hist: partes.append(texto("# Conversa até aqui\n" + hist))
    partes.append(texto("# Pedido do usuário\n" + str(mensagem).strip()[:4000]))
    r = cl.conversa(SISTEMA, esforco="medium").pedir(partes, schema(estilos), max_tokens=16000, rotulo="Chat do editor")
    return limpar(r, P, estilos)
