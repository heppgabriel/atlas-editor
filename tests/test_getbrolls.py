"""Get B-rolls como fonte principal da busca de B-roll, com o TikTok (Apify) de reserva.

Sem rede: a busca dos bancos é simulada; o download usa um vídeo gerado pelo ffmpeg num diretório temporário.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))


def setUpModule():
    global get_brolls, biblioteca, leva
    import get_brolls
    import biblioteca
    import leva


def cand(provider, ident, w=1080, h=1920, dur=12, url=None, kind="video"):
    return dict(provider=provider, source_id=str(ident), source_url=f"https://example.org/{provider}/{ident}",
                media_url=url if url is not None else f"https://cdn.example.org/{ident}.mp4", title=f"{provider} {ident}",
                media=dict(width=w, height=h, duration_s=dur, kind=kind), creator=dict(name="Autor"),
                rights=dict(license_name="Pexels License", license_url="https://www.pexels.com/license/", attribution="Autor"))


class VendorTests(unittest.TestCase):
    def test_copia_do_get_brolls_esta_no_repositorio(self):
        self.assertTrue(get_brolls.instalado(), "vendor/get-brolls/getbrolls/providers.py sumiu")
        pv = get_brolls._providers()
        self.assertIn("pexels", pv.capabilities())

    def test_linhas_reais_da_pexels_viram_candidatos_do_atlas(self):
        pv = get_brolls._providers()
        dados = {"videos": [{"id": 7, "url": "https://www.pexels.com/video/7/", "duration": 15, "image": "https://images.pexels.com/7.jpg",
                             "user": {"name": "Ana", "url": "https://www.pexels.com/@ana"},
                             "video_files": [{"file_type": "video/mp4", "link": "https://videos.pexels.com/7-hd.mp4", "width": 1080, "height": 1920}]}]}
        x = get_brolls.normalizar(pv._pexels_rows(dados)[0])
        self.assertEqual((x["fonte"], x["id"], x["arquivo_url"]), ("pexels", "7", "https://videos.pexels.com/7-hd.mp4"))
        self.assertEqual((x["largura"], x["altura"], x["dur"]), (1080, 1920, 15.0))
        self.assertEqual(x["licenca"], "Pexels License")


class BuscaTests(unittest.TestCase):
    def test_ignora_imagem_link_sem_https_e_video_curto(self):
        self.assertIsNone(get_brolls.normalizar(cand("commons", 1, kind="image")))
        self.assertIsNone(get_brolls.normalizar(cand("nasa", 2, url="http://x.org/a.mp4")))
        resultados = {"pexels": [cand("pexels", 3, dur=1)], "commons": [], "nasa": []}
        with patch.object(get_brolls, "_providers") as pv:
            pv.return_value.search.side_effect = lambda f, q, limit, media: resultados.get(f, [])
            achados, erros = get_brolls.buscar(["ocean"], fontes=["pexels", "commons", "nasa"])
        self.assertEqual(achados, []); self.assertEqual(erros, [])

    def test_prefere_video_em_pe_e_nao_repete(self):
        resultados = {"pexels": [cand("pexels", 1, w=1920, h=1080), cand("pexels", 2)],
                      "pixabay": [cand("pixabay", 9, w=720, h=1280)], "commons": [cand("pexels", 2)]}
        with patch.object(get_brolls, "_providers") as pv:
            pv.return_value.search.side_effect = lambda f, q, limit, media: resultados.get(f, [])
            achados, _ = get_brolls.buscar(["a", "b"], quantos=3, fontes=["pexels", "pixabay", "commons"])
        self.assertEqual([(x["fonte"], x["id"]) for x in achados], [("pexels", "2"), ("pixabay", "9"), ("pexels", "1")])

    def test_banco_que_falha_nao_derruba_a_busca(self):
        def busca(f, q, limit, media):
            if f == "pexels": raise ValueError("HTTP 401")
            return [cand("nasa", 5)]
        with patch.object(get_brolls, "_providers") as pv:
            pv.return_value.search.side_effect = busca
            achados, erros = get_brolls.buscar(["moon"], fontes=["pexels", "nasa"])
        self.assertEqual([x["id"] for x in achados], ["5"]); self.assertTrue(erros[0].startswith("Pexels"))

    def test_bancos_com_chave_entram_antes_de_commons_e_nasa(self):
        with patch.dict(os.environ, {"PEXELS_API_KEY": "x", "PIXABAY_API_KEY": ""}), patch.object(get_brolls, "chave", side_effect=lambda f: "x" if f == "pexels" else ""):
            self.assertEqual(get_brolls.fontes_ativas(), ["pexels", "commons", "nasa"])

    def test_trecho_fica_entre_2_e_10_segundos(self):
        self.assertEqual(get_brolls.trecho({"dur": 30}), (1.0, 10.0))
        self.assertEqual(get_brolls.trecho({"dur": 6}), (0.0, 6.0))
        self.assertEqual(get_brolls.trecho({"dur": 0}), (0.0, 10.0))

    def test_chave_da_biblioteca_e_por_banco_e_id(self):
        self.assertEqual(biblioteca.chave_de(dict(fonte="pexels", gb_id="7", arquivo="/x.mp4")), "pexels:7")


@unittest.skipUnless(shutil.which("ffmpeg"), "sem ffmpeg")
class DownloadTests(unittest.TestCase):
    def test_baixa_so_o_trecho_sem_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            fonte = os.path.join(tmp, "fonte.mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=25:duration=14",
                            "-f", "lavfi", "-i", "sine=duration=14", "-shortest", fonte], check=True)
            original = get_brolls.comando_ffmpeg
            semhttps = lambda url, ini, dur, saida: [a for a in original(url, ini, dur, saida) if a not in ("-protocol_whitelist", "https,tls,tcp,crypto")]
            x = get_brolls.normalizar(cand("pexels", 11, w=720, h=1280, dur=14, url="https://cdn.example.org/11.mp4"))
            x["arquivo_url"] = fonte
            with patch.object(get_brolls, "comando_ffmpeg", side_effect=semhttps):
                arq = get_brolls.baixar(x, os.path.join(tmp, "videos"))
            info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                                   "-of", "csv=p=0", arq], capture_output=True, text=True).stdout
            self.assertNotIn("audio", info)
            self.assertAlmostEqual(float(info.strip().splitlines()[-1]), 10.0, delta=0.3)
            self.assertFalse([f for f in os.listdir(os.path.dirname(arq)) if f.endswith(".part.mp4")])


class Ctx:
    def __init__(self):
        self.achados = {}; self.lock = threading.Lock(); self.falhas = []; self.guardados = []
        self.expert, self.oferta, self.nicho, self.leva_id = "Expert", "Oferta X", "X", "20260101-000000"
        class Est:
            def log(_, m): pass
        self.est = Est()
    def falha(self, fonte, b, erro): self.falhas.append((fonte, str(erro)))
    def guardar(self, b, ids, novos):
        self.guardados.append((b["nome"], list(ids)))
        if ids: self.achados[b["nome"]] = sorted(set(self.achados.get(b["nome"], [])) | set(ids))


class LevaTests(unittest.TestCase):
    def test_gb_uma_guarda_na_biblioteca_com_licenca(self):
        ctx, b = Ctx(), dict(nome="praia", categoria="Praia", termos=["beach waves", "ocean"], anuncios=["Anúncio 01"])
        x = get_brolls.normalizar(cand("pexels", 3))
        with patch.object(get_brolls, "buscar", return_value=([x], [])), patch.object(get_brolls, "baixar", return_value="/tmp/gb-pexels-3.mp4"), \
             patch.object(biblioteca, "pasta", return_value="/tmp"), patch.object(biblioteca, "adicionar", return_value="B0042") as add:
            leva.gb_uma(ctx, b)
        kw = add.call_args.kwargs
        self.assertEqual((kw["fonte"], kw["gb_id"], kw["licenca"], kw["categoria"]), ("pexels", "3", "Pexels License", "Praia"))
        self.assertEqual(ctx.guardados, [("praia", ["B0042"])]); self.assertEqual(ctx.falhas, [])

    def test_gb_uma_sem_resultado_e_com_erro_registra_falha(self):
        ctx, b = Ctx(), dict(nome="x", categoria="X", termos=["x"], anuncios=[])
        with patch.object(get_brolls, "buscar", return_value=([], ["Pexels: HTTP 401"])):
            leva.gb_uma(ctx, b)
        self.assertEqual(ctx.falhas, [("Get B-rolls", "Pexels: HTTP 401")])

    def test_reserva_so_pega_buscas_com_poucos_clipes(self):
        ctx = Ctx(); ctx.achados = {"a": ["B1", "B2", "B3"], "b": ["B4"]}
        buscas = [dict(nome="a"), dict(nome="b"), dict(nome="c")]
        self.assertEqual([b["nome"] for b in leva.faltando(ctx, buscas)], ["b", "c"])


if __name__ == "__main__":
    unittest.main()
