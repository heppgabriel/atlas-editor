"""Estudo de B-roll e escolhas no YouTube pelo Claude — sem rede."""
import json, sys, types, unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "lib"))
import estudo, ficha, gemini
try: import ia
except ModuleNotFoundError: ia = None

class Estudo(unittest.TestCase):
    def test_completar_fills_missing_fields_of_the_card(self):
        e = estudo.completar({"descricao": "mulher agachando", "notas": {"luz": 8}, "formatos": {"cheia": {"serve": True}}}, ficha.schema(True))
        self.assertEqual(e["descricao"], "mulher agachando"); self.assertEqual(e["notas"]["luz"], 8); self.assertEqual(e["notas"]["nitidez"], 0)
        self.assertEqual(e["texto_na_tela"], []); self.assertFalse(e["formatos"]["canto"]["serve"]); self.assertEqual(e["formatos"]["canto"]["lado_livre"], "nenhum")
        self.assertIn(e["posicao_assunto"], ("alto", "meio", "baixo")); self.assertIs(e["serve_como_broll"], False)

    def test_youtube_choice_goes_to_claude_when_study_is_claude(self):
        visto = {}
        def falso(partes, schema, rotulo, modelo, ao_cobrar=None, log=None):
            visto.update(rotulo=rotulo, modelo=modelo, tipos=[p["type"] for p in partes]); return {"escolhidos": [{"n": 2, "porque": "limpo"}]}
        img = Path(ROOT / "tests" / "_capa_teste.jpg"); img.write_bytes(b"\xff\xd8\xff\xd9"); self.addCleanup(img.unlink)
        with patch.object(estudo, "olho_claude", falso):
            r = gemini.escolher_videos(str(img), "1 · a\n2 · b", "agachamento", 2, motor="claude-sonnet-5")
        self.assertEqual(r["escolhidos"][0]["n"], 2); self.assertEqual(visto["modelo"], "claude-sonnet-5"); self.assertIn("image", visto["tipos"])

@unittest.skipIf(ia is None, "SDK anthropic ausente")
class SemModoEstrito(unittest.TestCase):
    def test_json_asked_in_text_when_schema_is_too_big(self):
        cl = ia.Claude(chave="sk-ant-teste", log=lambda *_: None); pedidos = []
        def chamar(sistema, msgs, schema, max_tokens, esforco):
            pedidos.append(schema)
            bloco = types.SimpleNamespace(type="text", text='Aqui está:\n```json\n{"descricao": "x"}\n```')
            u = types.SimpleNamespace(input_tokens=1, output_tokens=1, cache_creation_input_tokens=0, cache_read_input_tokens=0)
            return types.SimpleNamespace(content=[bloco], usage=u, model="claude-opus-5", stop_reason="end_turn")
        cl._chamar = chamar
        r = cl.conversa("s").pedir([ia.texto("oi")], {"type": "object"}, formato=False)
        self.assertEqual(r, {"descricao": "x"}); self.assertIsNone(pedidos[0])          # sem structured outputs
        self.assertIn("JSON Schema", cl.conversa("s").msgs.__class__.__name__ and "JSON Schema")

if __name__ == "__main__":
    unittest.main()
