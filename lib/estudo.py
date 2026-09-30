"""Estudo de B-roll pelo Claude (no lugar do Gemini). Roda no Python da .venv (SDK anthropic).

Cada clipe vira UMA folha de contato com 12 a 16 quadros espalhados, com o segundo de cada um, e o Claude devolve a mesma
ficha completa do Gemini (lib/ficha.py). O Gemini é o padrão (assiste o vídeo, mais barato); o Claude entra sem ele.
É feito uma vez por clipe: a ficha fica na biblioteca e toda edição depois só lê o texto dela (barato).
Precisão dos trechos: o intervalo entre dois quadros (~1,5–3 s); texto que aparece e some entre dois quadros pode escapar.

  .venv/bin/python lib/estudo.py folha <clipe.mp4> <saida.jpg>     -> só monta a folha (não gasta nada)"""
import os, sys, json, math, shutil, tempfile, subprocess
from concurrent.futures import ThreadPoolExecutor

LIB = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, LIB)
PY_SISTEMA = sys.executable                      # folhas.py usa o PIL do Python do sistema
PATH = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "/usr/bin:/bin")

import ficha
SCH = ficha.schema(estrito=True)                           # a mesma ficha do Gemini (lib/ficha.py)
INSTR = ficha.instrucoes(video=False)

def modelo_padrao():
    import chaves
    m = chaves.ler().get("modelo_estudo") or "claude-opus-5"
    return m if m.startswith("claude") else "claude-opus-5"

def duracao(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                       capture_output=True, text=True, env=dict(os.environ, PATH=PATH))
    try: return float(r.stdout.strip())
    except ValueError: return 0.0

def folha(arq, saida, dur=None):
    """Folha 4 colunas × 3-4 linhas com o segundo de cada quadro. Devolve (saida, [segundos])."""
    dur = dur or duracao(arq)
    if dur <= 0: raise RuntimeError("não consegui ler a duração do clipe")
    n = int(max(12, min(16, math.ceil(dur / 2.0))))
    ts = [round(dur * (k + 0.5) / n, 1) for k in range(n)]; tmp = tempfile.mkdtemp(prefix="estudo_")
    try:
        def um(t):
            o = os.path.join(tmp, f"{t:07.1f}.jpg")
            subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", str(t), "-i", arq, "-frames:v", "1", "-vf",
                            "scale=300:533:force_original_aspect_ratio=decrease", o], env=dict(os.environ, PATH=PATH))
            return o
        with ThreadPoolExecutor(4) as ex: imgs = list(ex.map(um, ts))
        subprocess.run([PY_SISTEMA, os.path.join(LIB, "folhas.py"), saida, "4", "300", "533", *[f"{i}::{t:.1f} s" for i, t in zip(imgs, ts)]],
                       check=True, env=dict(os.environ, PATH=PATH))
    finally: shutil.rmtree(tmp, ignore_errors=True)
    return saida, ts

def estudar(arq, contexto="", cl=None, rotulo="estudo"):
    """cl: ia.Claude (já com a chave e o modelo). Devolve o estudo no formato da biblioteca."""
    import ia
    dur = duracao(arq); tmp = tempfile.mkdtemp(prefix="folha_")
    try:
        f, ts = folha(arq, os.path.join(tmp, "folha.jpg"), dur)
        conv = cl.conversa(INSTR, esforco="low")
        # A ficha é grande demais para o modo estrito da API ("The compiled grammar is too large"): o formato vai no
        # texto do pedido e a ficha é completada com os campos que faltarem.
        e = conv.pedir([ia.imagem(f), ia.texto(f"O clipe tem {dur:.1f} s. Quadros em: {', '.join(f'{t:.1f}' for t in ts)} s."
                                              + (f"\nContexto da busca: {contexto}" if contexto else ""))], SCH, max_tokens=12000, rotulo=rotulo,
                       formato=False)
        e = completar(e, SCH)
    finally: shutil.rmtree(tmp, ignore_errors=True)
    return ficha.ajustar(e, dur)

def completar(v, sch):
    """Preenche o que a resposta deixou de fora com o valor neutro do tipo (lista vazia, 0, falso, texto vazio)."""
    t = sch.get("type")
    if t == "object":
        v = v if isinstance(v, dict) else {}
        for k, s in (sch.get("properties") or {}).items(): v[k] = completar(v.get(k), s)
        return v
    if t == "array": return [completar(x, sch.get("items") or {}) for x in v] if isinstance(v, list) else []
    if v is not None:
        if t in ("number", "integer") and not isinstance(v, (int, float)):
            try: return float(v)
            except (TypeError, ValueError): return 0
        return v
    return {"string": (sch.get("enum") or [""])[-1] if sch.get("enum") else "", "number": 0, "integer": 0, "boolean": False}.get(t)

def olho_claude(partes, schema, rotulo, modelo, ao_cobrar=None, log=None):
    """As escolhas pelo olho no YouTube (capas e folha de quadros) pelo Claude, no lugar do Gemini: são só imagens."""
    import ia, base64
    blocos = []
    for p in partes:
        if p.get("type") == "image":
            blocos.append({"type": "image", "source": {"type": "base64", "media_type": p.get("mime_type") or "image/jpeg", "data": p["data"]}})
        elif p.get("type") == "text": blocos.append({"type": "text", "text": p["text"]})
    cl = ia.Claude(modelo=modelo, log=log or (lambda *_: None), ao_cobrar=ao_cobrar)
    return cl.conversa("Você é o olho de um editor de vídeo escolhendo imagem de apoio (B-roll) para anúncios verticais.", esforco="low").pedir(blocos, schema, max_tokens=6000, rotulo=rotulo)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["folha"]: print(folha(a[1], a[2]))
    else: print(__doc__)
