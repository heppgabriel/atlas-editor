"""Busca de B-roll pelo Get B-rolls (github.com/engenheirodevideo/get-brolls, MIT): Pexels, Pixabay, Wikimedia Commons e NASA.

A cópia fica em vendor/get-brolls (só o pacote Python, travado na versão do VENDOR). Daqui o Atlas usa a
busca (`providers.search`), que já devolve o link do arquivo de vídeo, a licença e o autor; o download e o corte
são do Atlas (ffmpeg), e cada clipe entra na biblioteca como os do TikTok e do YouTube: o estudo (Gemini ou Claude)
depois decide o que presta.

O YouTube continua pela busca do próprio Atlas (lib/youtube.py), que já escolhe os trechos com a IA. A Apify
(TikTok) virou reserva: só entra nas buscas em que o Get B-rolls e o YouTube trouxeram pouco (lib/leva.py).

Chaves: Pexels e Pixabay são grátis e opcionais (⚙ Configurações › Bancos de vídeo, ou PEXELS_API_KEY e
PIXABAY_API_KEY no ambiente). Sem elas, a busca fica no Commons e na NASA, que não pedem chave."""
import os, re, sys, shutil, secrets, subprocess

LIB = os.path.dirname(os.path.abspath(__file__)); SKILL = os.path.dirname(LIB)
VENDOR = os.path.join(SKILL, "vendor", "get-brolls")
VERSAO = "2.5.0"
FONTES = ("pexels", "pixabay", "commons", "nasa")
CHAVES = {"pexels": "PEXELS_API_KEY", "pixabay": "PIXABAY_API_KEY"}
NOMES = {"pexels": "Pexels", "pixabay": "Pixabay", "commons": "Wikimedia Commons", "nasa": "NASA"}
DUR_MAX, DUR_MIN = 10.0, 2.0          # o trecho que vai para a biblioteca (mesma faixa dos trechos do YouTube)

class ErroGetBrolls(RuntimeError): pass

def instalado(): return os.path.isfile(os.path.join(VENDOR, "getbrolls", "providers.py"))

def chave(fonte):
    """Ambiente primeiro, depois ⚙ Configurações."""
    v = os.environ.get(CHAVES[fonte], "").strip()
    if v: return v
    try:
        import chaves
        return str(chaves.ler().get(fonte) or "").strip()
    except Exception: return ""

def fontes_ativas():
    """Os bancos com chave entram primeiro (são os que mais acham imagem de anúncio); Commons e NASA sempre."""
    return [f for f in ("pexels", "pixabay") if chave(f)] + ["commons", "nasa"]

def _providers():
    if not instalado(): raise ErroGetBrolls("o Get B-rolls não está instalado (vendor/get-brolls): rode o install.sh de novo")
    os.environ.setdefault("GB_CACHE_DIR", os.path.join(os.path.expanduser("~"), ".cache", "atlas-getbrolls"))
    os.environ.setdefault("GB_LIBRARY", "off")      # a memória editorial do Get B-rolls é por pessoa; o Atlas tem a biblioteca dele
    os.environ.setdefault("GB_LOG_LEVEL", "off")
    for f, env in CHAVES.items():
        k = chave(f)
        if k: os.environ[env] = k
    if VENDOR not in sys.path: sys.path.insert(0, VENDOR)
    from getbrolls import providers
    return providers

def normalizar(c):
    """Candidato do Get B-rolls -> o que o Atlas precisa para baixar e guardar. None se não for um vídeo baixável."""
    media = c.get("media") or {}
    url = c.get("media_url")
    if not url or not str(url).startswith("https://"): return None
    if (media.get("kind") or "video") != "video" or c.get("asset_type") == "image": return None
    rights = c.get("rights") or {}; criador = c.get("creator") or {}
    w, h = media.get("width") or 0, media.get("height") or 0
    return dict(fonte=c.get("provider"), id=str(c.get("source_id") or ""), url=c.get("source_url") or "", arquivo_url=url,
                titulo=str(c.get("title") or "")[:200], autor=str(criador.get("name") or "")[:120],
                largura=int(w or 0), altura=int(h or 0), dur=float(media.get("duration_s") or 0),
                licenca=str(rights.get("license_name") or "")[:120], licenca_url=rights.get("license_url") or "",
                atribuicao=str(rights.get("attribution") or "")[:200])

def nota(x):
    """Ordem de preferência: em pé (o anúncio é vertical), duração que dá um trecho bom, resolução."""
    w, h, d = x["largura"], x["altura"], x["dur"]
    em_pe = 2 if h > w > 0 else 1 if w == h or not (w and h) else 0
    cabe = 1 if d == 0 or d >= 4 else 0
    return (em_pe, cabe, min(w, h))

def buscar(termos, quantos=4, fontes=None, log=print):
    """Os melhores `quantos` vídeos para os termos (em inglês), dos bancos ativos. Devolve (lista, erros)."""
    pv = _providers(); fontes = list(fontes or fontes_ativas())
    achados, vistos, erros = [], set(), []
    for termo in [t for t in termos if str(t).strip()][:2]:
        for f in fontes:
            try: cands = pv.search(f, str(termo).strip()[:300], limit=8, media="video")
            except Exception as ex:
                erros.append(f"{NOMES.get(f, f)}: {str(ex)[:160]}"); continue
            for c in cands:
                x = normalizar(c)
                if not x or (x["fonte"], x["id"]) in vistos: continue
                if x["dur"] and x["dur"] < DUR_MIN: continue
                vistos.add((x["fonte"], x["id"])); x["termo"] = str(termo).strip(); achados.append(x)
    achados.sort(key=nota, reverse=True)
    return achados[:quantos], erros

def trecho(x):
    """(início, duração) do pedaço que vai para a biblioteca: pula o primeiro segundo dos vídeos longos (costuma
    ter a entrada de câmera) e fica com até DUR_MAX segundos."""
    d = x.get("dur") or 0
    ini = 1.0 if d >= DUR_MAX + 2 else 0.0
    dur = DUR_MAX if not d else max(DUR_MIN, min(DUR_MAX, d - ini))
    return ini, dur

def comando_ffmpeg(url, ini, dur, saida):
    """Baixa só o trecho e já entrega como os outros B-rolls: H.264, sem áudio, lado maior até 1920, 30 fps."""
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-protocol_whitelist", "https,tls,tcp,crypto",
            "-ss", f"{ini:.2f}", "-t", f"{dur:.2f}", "-i", url, "-an",
            "-vf", "scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))',fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-movflags", "+faststart", saida]

def slug(s, n=40):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower()
    return s[:n] or "clipe"

def baixar(x, pasta):
    """Baixa o trecho para `pasta` e devolve o caminho. Grava num .part e troca no fim (duas buscas podem mirar o mesmo vídeo)."""
    if not shutil.which("ffmpeg"): raise ErroGetBrolls("falta o ffmpeg")
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, f"gb-{x['fonte']}-{slug(x['id'], 60)}.mp4")
    if os.path.isfile(destino) and os.path.getsize(destino) > 0: return destino
    ini, dur = trecho(x)
    parcial = destino + "." + secrets.token_hex(6) + ".part.mp4"
    try:
        r = subprocess.run(comando_ffmpeg(x["arquivo_url"], ini, dur, parcial), capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or not os.path.isfile(parcial) or os.path.getsize(parcial) < 1000:
            raise ErroGetBrolls(f"download falhou ({NOMES.get(x['fonte'], x['fonte'])}): " + ((r.stderr or "").strip().splitlines() or ["ffmpeg falhou"])[-1][:200])
        os.replace(parcial, destino)
        return destino
    finally:
        if os.path.exists(parcial): os.remove(parcial)

def campos_biblioteca(x):
    """O que vai para biblioteca.adicionar (além de arquivo, termos, expert, oferta, categoria e leva)."""
    return dict(fonte=x["fonte"], gb_id=x["id"], url=x["url"], autor=x["autor"], titulo=x["titulo"],
                licenca=x["licenca"], licenca_url=x["licenca_url"], atribuicao=x["atribuicao"], busca="getbrolls")
