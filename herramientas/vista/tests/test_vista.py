"""Tests de la vista. Solo stdlib: python3 -m unittest discover -s tests"""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import vista  # noqa: E402


def config():
    return {
        "version": 1,
        "buzon": "buzon",
        "roles": {
            "qa": {
                "modelo": "test/modelo",
                "entorno": "opencode",
                "cwd": ".",
                "acceso": [{"ruta": ".", "modo": "rw"}],
                "trigger": {"modo": "agente", "desde": ["constructor"], "cada": None},
                "comando": "true",
                "entrega": ["evidencia"],
            },
            "usuario": {
                "tipo": "humano",
                "modelo": None,
                "entorno": None,
                "cwd": ".",
                "acceso": [{"ruta": ".", "modo": "rw"}],
                "trigger": {"modo": "usuario", "desde": [], "cada": None},
                "comando": None,
                "entrega": [],
            },
        },
    }


class VistaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.cfg = os.path.join(self.dir, "reparto.json")
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(config(), fh)
        os.makedirs(os.path.join(self.dir, "buzon", "qa"))
        os.makedirs(os.path.join(self.dir, ".watcher", "turno"))
        os.makedirs(os.path.join(self.dir, ".watcher", "logs"))

        with open(os.path.join(self.dir, ".watcher", "turno", "qa.json"), "w", encoding="utf-8") as fh:
            json.dump({"rol": "qa", "estado": "trabajando", "con": "constructor",
                       "handoff_id": "h-001", "desde": "2026-10-24T10:00:00-0300"}, fh)
        with open(os.path.join(self.dir, ".watcher", "eventos.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": "2026-10-24T10:00:00-0300", "rol": "qa",
                                 "accion": "despierta", "con": "constructor",
                                 "handoff_id": "h-001"}) + "\n")
        with open(os.path.join(self.dir, ".watcher", "logs", "qa.log"), "w", encoding="utf-8") as fh:
            fh.write("linea uno\nveredicto: aprobado\n")
        with open(os.path.join(self.dir, "buzon", "qa", "msg-001.json"), "w", encoding="utf-8") as fh:
            json.dump({"handoff_id": "h-pend", "estado": "entregado",
                       "de": "constructor", "para": "qa"}, fh)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), vista.crear_handler(self.cfg))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        # El proxy de egreso del host responde 502 para loopback: se saltea en tests.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def get(self, ruta):
        try:
            with self.opener.open(self.base + ruta, timeout=5) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def test_estado_arma_roles(self):
        datos = vista.construir_estado(self.cfg)
        roles = {r["nombre"]: r for r in datos["roles"]}
        self.assertEqual(roles["qa"]["estado"], "trabajando")
        self.assertEqual(roles["qa"]["con"], "constructor")
        self.assertEqual(roles["qa"]["pendientes"], ["h-pend"])
        self.assertIn("veredicto: aprobado", roles["qa"]["log"])
        self.assertEqual(roles["usuario"]["estado"], "no aplica")

    def test_api_estado(self):
        codigo, cuerpo = self.get("/api/estado")
        self.assertEqual(codigo, 200)
        datos = json.loads(cuerpo)
        self.assertEqual(len(datos["roles"]), 2)
        self.assertEqual(datos["eventos"][0]["accion"], "despierta")

    def test_index(self):
        codigo, cuerpo = self.get("/")
        self.assertEqual(codigo, 200)
        self.assertIn("Ciclo de agentes", cuerpo)
        self.assertIn("/api/estado", cuerpo)

    def test_api_log(self):
        codigo, cuerpo = self.get("/api/log?rol=qa")
        self.assertEqual(codigo, 200)
        self.assertIn("veredicto: aprobado", cuerpo)

    def test_api_log_rol_desconocido(self):
        codigo, _ = self.get("/api/log?rol=nadie")
        self.assertEqual(codigo, 404)

    def test_404(self):
        codigo, _ = self.get("/nada")
        self.assertEqual(codigo, 404)


if __name__ == "__main__":
    unittest.main()
