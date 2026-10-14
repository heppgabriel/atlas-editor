"""Chat do editor: o contexto que vai para o Claude e a conferência das operações que voltam. Sem rede: o Claude é simulado."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))


def setUpModule():
    global chat_editor, ia
    import chat_editor
    import ia


E = {"nome": "Teste", "descricao": "modelo", "regras": {"palavras_max": 4},
     "letreiro": {"topo_padrao": 0.12, "estilos": {"sans": {"rotulo": "Branca pequena"}, "num": {"rotulo": "Número grande"}}}}


def plano():
    return {"dur": 60.0, "estilo": "teste",
            "legendas": [{"ini": 10.0, "fim": 11.0, "txt": "no dia sete", "pals": [["no", 10.0, 10.2], ["dia", 10.2, 10.5], ["sete", 10.5, 11.0]]},
                         {"ini": 20.0, "fim": 21.0, "txt": "dia catorze"}],
            "blocos": [{"linhas": [["sans", "OI", 2.0, None]], "fim": 3.0, "topo": 0.12}],
            "cenas": [{"ini": 5.0, "fim": 7.0, "tipo": "cheia", "id": "B0001", "src": "/x.mp4"}],
            "escuro": [[30.0, 32.0]], "pb": [], "flash": [40.0], "glitch": [[45.0, 0.3]]}


def op(**kw):
    base = dict(op="add_letreiro", i=-1, linhas=[], ini=-1, fim=-1, topo=-1, tipo="", ocultar=False)
    base.update(kw); return base


class ContextoTests(unittest.TestCase):
    def test_fala_vem_com_o_tempo_de_cada_palavra(self):
        c = chat_editor.contexto(plano(), E, agora=12.5)
        self.assertIn("dia@10.2", c); self.assertIn("sete@10.5", c)
        self.assertIn("legenda 1 [20.0–21.0]: dia catorze", c)
        self.assertIn("letreiro 0 [2.0–3.0]", c); self.assertIn("B-roll 0 [5.0–7.0] cheia · B0001", c)
        self.assertIn("flash 0 em 40.0", c); self.assertIn("glitch 0 [45.0–45.3]", c)
        self.assertIn("- num: Número grande", c); self.assertIn("palavras_max", c); self.assertIn("cursor do editor em 12.5", c)

    def test_schema_so_aceita_estilos_do_template(self):
        sch = chat_editor.schema(["sans", "num"])
        estilo = sch["properties"]["operacoes"]["items"]["properties"]["linhas"]["items"]["properties"]["estilo"]
        self.assertEqual(estilo["enum"], ["sans", "num"])


class LimparTests(unittest.TestCase):
    def test_letreiro_valido_passa_com_linhas_em_ordem(self):
        r = chat_editor.limpar({"resposta": "ok", "operacoes": [
            op(linhas=[{"estilo": "num", "texto": "7", "t": 10.3}, {"estilo": "sans", "texto": "DIA", "t": 10.1}], fim=12.0)]}, plano(), ["sans", "num"])
        self.assertEqual(r["descartadas"], 0)
        self.assertEqual([l["texto"] for l in r["operacoes"][0]["linhas"]], ["DIA", "7"])

    def test_descarta_indice_inexistente_tempo_fora_e_estilo_desconhecido(self):
        r = chat_editor.limpar({"resposta": "", "operacoes": [
            op(op="apagar_letreiro", i=5),
            op(linhas=[{"estilo": "num", "texto": "7", "t": 99}], fim=100),
            op(linhas=[{"estilo": "inventado", "texto": "7", "t": 10}], fim=12),
            op(op="apagar_efeito", tipo="flash", i=0),
            op(op="add_efeito", tipo="pb", ini=15, fim=18),
            op(op="legenda", i=1, ocultar=True)]}, plano(), ["sans", "num"])
        self.assertEqual(r["descartadas"], 3)
        self.assertEqual([o["op"] for o in r["operacoes"]], ["apagar_efeito", "add_efeito", "legenda"])

    def test_letreiro_que_termina_antes_da_ultima_linha_e_descartado(self):
        r = chat_editor.limpar({"operacoes": [op(linhas=[{"estilo": "num", "texto": "7", "t": 10}], fim=9)]}, plano(), ["num"])
        self.assertEqual((r["operacoes"], r["descartadas"]), ([], 1))


class ResponderTests(unittest.TestCase):
    def test_responder_pede_ao_claude_e_devolve_operacoes_conferidas(self):
        visto = {}
        class Conv:
            def pedir(self, partes, schema, max_tokens, rotulo):
                visto["texto"] = "\n".join(p["text"] for p in partes)
                return {"resposta": "Coloquei DIA 7 em 0:10.", "operacoes": [
                    op(linhas=[{"estilo": "sans", "texto": "DIA", "t": 10.1}, {"estilo": "num", "texto": "7", "t": 10.4}], fim=12.0)]}
        class Cl:
            def __init__(self, **kw): visto["ao_cobrar"] = kw.get("ao_cobrar")
            def conversa(self, sistema, esforco): visto["sistema"] = sistema; return Conv()
        with patch.object(chat_editor.ia, "Claude", Cl):
            r = chat_editor.responder("/tmp/proj", plano(), E, "letreiro em cada dia", [{"quem": "eu", "txt": "oi"}], agora=3)
        self.assertEqual(r["resposta"], "Coloquei DIA 7 em 0:10."); self.assertEqual(len(r["operacoes"]), 1)
        self.assertIn("Pedido do usuário\nletreiro em cada dia", visto["texto"]); self.assertIn("Usuário: oi", visto["texto"])
        self.assertTrue(callable(visto["ao_cobrar"]))


if __name__ == "__main__":
    unittest.main()
