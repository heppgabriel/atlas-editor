"""Chaves de API do Estúdio (Claude, Gemini, Apify, Pexels/Pixabay do Get B-rolls e a IA generativa do Ad Animado) e os modelos escolhidos para a edição automática.
Ficam só neste Mac, em ~/.config/estudio-edicao/chaves.json (permissão 600), fora das pastas que o servidor
serve. A página nunca recebe a chave inteira: só se está configurada e os 4 últimos caracteres."""
import os, json

ARQ = os.path.abspath(os.path.expanduser(os.environ.get("ESTUDIO_CHAVES") or "~/.config/estudio-edicao/chaves.json"))
PASTA = os.path.dirname(ARQ)
MODELOS = [dict(id="claude-opus-5-5", nome="Claude Opus 5.5 (recomendado)"),
           dict(id="claude-sonnet-5-5", nome="Claude Sonnet 5.5 (mais barato)"),
           dict(id="claude-opus-5", nome="Claude Opus 5"),
           dict(id="claude-sonnet-5", nome="Claude Sonnet 5")]
PADRAO = dict(anthropic="", gemini="", openrouter="", apify="", openai="", heygen="", xai="", pexels="", pixabay="",
              modelo="claude-opus-5-5", modelo_gemini="gemini-3.8-flash", modelo_estudo="gemini",
              gen_provedor="grok", gen_resolucao="720p", gen_auth="assinatura", gen_modelo_img="grok-imagine-image",
              kie="", gen_img="grok", gen_video="grok", claude_auth="api", claude_token="", gemini_gratis=False)
AUTH_CLAUDE = [dict(id="api", nome="Chave da API da Anthropic (paga por uso)"),
               dict(id="assinatura", nome="Minha assinatura do Claude (Pro/Max) — usa o limite do plano, pelo Claude Code deste computador")]
def claude_ok():
    """Dá para chamar o Claude? Pela chave da API, ou pela assinatura (o login do Claude Code / token do setup-token)."""
    d = ler()
    return bool(d.get("anthropic")) or (d.get("claude_auth") == "assinatura")
# IA generativa (imagem e vídeo) do Ad Animado. Um provedor por enquanto (Grok, da xAI); lib/gerativa.py
# é quem fala com a API — um provedor novo entra lá e aqui na lista.
GERATIVAS = [dict(id="grok", nome="Grok Imagine (xAI)", chave="xai")]
# Como o Atlas fala com o Grok: pela assinatura (o mesmo login do `grok` no terminal, ~/.grok/auth.json — usa a cota
# semanal, sem cobrança por uso) ou por uma chave de API da xAI (cobrada por imagem/segundo de vídeo).
AUTH_GERATIVA = [dict(id="assinatura", nome="Assinatura do Grok (o mesmo login do terminal · usa a cota semanal)"),
                 dict(id="api", nome="Chave de API da xAI (cobra por uso)")]
MODELOS_IMG = [dict(id="grok-imagine-image", nome="Grok Imagine (padrão, mais rápido)"),
               dict(id="grok-imagine-image-quality", nome="Grok Imagine Quality (melhor qualidade)")]
def assinatura_grok(): return os.path.expanduser("~/.grok/auth.json")
RESOLUCOES = [dict(id="480p", nome="480p (mais barato, para testar)"), dict(id="720p", nome="720p (recomendado)"),
              dict(id="1080p", nome="1080p (mais caro)")]
ESTUDO = [dict(id="gemini", nome="Gemini (assiste o vídeo segundo a segundo; ~US$ 0,01 por clipe, uma vez)"),
          dict(id="claude-opus-5-5", nome="Claude Opus 5.5 (pela folha de quadros · API ~US$ 0,04 por clipe, ou pela sua assinatura)"),
          dict(id="claude-sonnet-5-5", nome="Claude Sonnet 5.5 (pela folha de quadros · API ~US$ 0,02 por clipe, ou pela sua assinatura)"),
          dict(id="claude-opus-5", nome="Claude Opus 5 (pela folha de quadros · API ~US$ 0,05 por clipe, ou pela sua assinatura)"),
          dict(id="claude-sonnet-5", nome="Claude Sonnet 5 (pela folha de quadros · API ~US$ 0,02 por clipe, ou pela sua assinatura)")]

def ler():
    d = dict(PADRAO)
    if os.path.exists(ARQ):
        try: d.update(json.load(open(ARQ)))
        except ValueError: pass
    return d

def gravar(**novos):
    d = ler()
    for k, v in novos.items():
        if v is None: continue
        d[k] = v.strip() if isinstance(v, str) else v
    os.makedirs(PASTA, mode=0o700, exist_ok=True); os.chmod(PASTA, 0o700)
    tmp = ARQ + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(d, f, indent=1)
    os.replace(tmp, ARQ); os.chmod(ARQ, 0o600)
    return d

def publico():
    """O que a página pode ver."""
    import gemini, gerativa
    d = ler(); final = lambda k: ("…" + k[-4:]) if len(k or "") > 8 else ""
    return dict(anthropic=dict(ok=bool(d["anthropic"]), final=final(d["anthropic"])),
                claude_auth=d.get("claude_auth") or "api", auths_claude=AUTH_CLAUDE, gemini_gratis=bool(d.get("gemini_gratis")),
                claude_token=dict(ok=bool(d.get("claude_token")), final=final(d.get("claude_token", ""))),
                gemini=dict(ok=bool(d.get("gemini")), final=final(d.get("gemini", ""))),
                openrouter=dict(ok=bool(d.get("openrouter")), final=final(d.get("openrouter", ""))),
                apify=dict(ok=bool(d["apify"]), final=final(d["apify"])),
                pexels=dict(ok=bool(d.get("pexels")), final=final(d.get("pexels", ""))),
                pixabay=dict(ok=bool(d.get("pixabay")), final=final(d.get("pixabay", ""))),
                openai=dict(ok=bool(d.get("openai")), final=final(d.get("openai", ""))),
                heygen=dict(ok=bool(d.get("heygen")), final=final(d.get("heygen", ""))),
                xai=dict(ok=bool(d.get("xai")), final=final(d.get("xai", ""))),
                gen_provedor=d.get("gen_provedor") or PADRAO["gen_provedor"], gerativas=GERATIVAS,
                gen_resolucao=d.get("gen_resolucao") or PADRAO["gen_resolucao"], resolucoes=RESOLUCOES,
                gen_auth=d.get("gen_auth") or PADRAO["gen_auth"], auths=AUTH_GERATIVA, assinatura_ok=os.path.exists(assinatura_grok()),
                gen_modelo_img=d.get("gen_modelo_img") or PADRAO["gen_modelo_img"], modelos_img=MODELOS_IMG,
                kie=dict(ok=bool(gerativa.chave_kie()), final=final(gerativa.chave_kie()), detectada=bool(gerativa.chave_kie()) and not d.get("kie")),
                gen_img=d.get("gen_img") or "grok", gen_video=d.get("gen_video") or "grok",
                modelos_imagem=gerativa.MODELOS_IMAGEM, modelos_video=gerativa.MODELOS_VIDEO,
                modelo=d.get("modelo") or PADRAO["modelo"], modelos=MODELOS,
                modelo_gemini=d.get("modelo_gemini") or PADRAO["modelo_gemini"], modelos_gemini=gemini.MODELOS,
                modelo_estudo=d.get("modelo_estudo") or PADRAO["modelo_estudo"], estudos=ESTUDO)
