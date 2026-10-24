"""Tests del watcher. Solo stdlib: python3 -m unittest discover -s tests"""

import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WATCHER = os.path.join(os.path.dirname(HERE), "watcher.py")


def config(salida, comando=True, modo="agente", desde=("orquestador",), cada=None):
    if comando is True:
        codigo = ("import os;open(%r,'a',encoding='utf-8')"
                  ".write((os.environ.get('REPARTO_HANDOFF_ID') or '?')+chr(10))" % salida)
        comando = "%s -c %s" % (shlex.quote(sys.executable), shlex.quote(codigo))
    return {
        "version": 1,
        "buzon": "buzon",
        "roles": {
            "qa": {
                "modelo": "x/modelo",
                "entorno": "opencode",
                "cwd": ".",
                "acceso": [{"ruta": ".", "modo": "rw"}],
                "trigger": {"modo": modo, "desde": list(desde), "cada": cada},
                "comando": comando,
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


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.cfg = os.path.join(self.dir, "reparto.json")
        self.salida = os.path.join(self.dir, "salida.txt")
        self.buzon = os.path.join(self.dir, "buzon", "qa")
        os.makedirs(self.buzon)
        self.escribir(config(self.salida))

    def tearDown(self):
        self.tmp.cleanup()

    def escribir(self, datos):
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)

    def handoff(self, nombre="msg-001.json", estado="pedido", de="orquestador",
                para="qa", hid="h-001"):
        ruta = os.path.join(self.buzon, nombre)
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump({"handoff_id": hid, "estado": estado, "de": de, "para": para,
                       "reply_to": None, "pedido": "x", "artefactos": {}, "criterios": []},
                      fh)
        return ruta

    def correr(self, *args):
        proc = subprocess.run([sys.executable, WATCHER, *args, "--config", self.cfg],
                              capture_output=True, text=True, timeout=60)
        return proc.returncode, proc.stdout + proc.stderr

    def leidas(self):
        if not os.path.exists(self.salida):
            return []
        with open(self.salida, encoding="utf-8") as fh:
            return [l for l in fh.read().splitlines() if l]

    def test_despierta_con_pedido(self):
        self.handoff(hid="h-abc")
        codigo, salida = self.correr("qa", "--once")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("DESPIERTA qa", salida)
        self.assertEqual(self.leidas(), ["h-abc"])

    def test_no_repite_el_mismo_archivo(self):
        self.handoff()
        self.correr("qa", "--once")
        self.correr("qa", "--once")
        self.assertEqual(len(self.leidas()), 1)

    def test_archivo_modificado_despierta_de_nuevo(self):
        ruta = self.handoff(hid="h-001")
        self.correr("qa", "--once")
        datos = json.load(open(ruta, encoding="utf-8"))
        datos["estado"] = "reabierto"
        datos["handoff_id"] = "h-002"
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        os.utime(ruta, None)
        self.correr("qa", "--once")
        self.assertEqual(self.leidas(), ["h-001", "h-002"])

    def test_respeta_desde(self):
        self.handoff(de="constructor", hid="h-no")
        codigo, salida = self.correr("qa", "--once")
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.leidas(), [])

    def test_no_despierta_su_propio_mensaje(self):
        self.handoff(de="qa", hid="h-yo")
        self.correr("qa", "--once")
        self.assertEqual(self.leidas(), [])

    def test_estado_que_no_requiere_accion(self):
        self.handoff(estado="en_curso", hid="h-curso")
        self.correr("qa", "--once")
        self.assertEqual(self.leidas(), [])

    def test_lock_ocupado_no_despierta(self):
        self.handoff(hid="h-lock")
        estado_dir = os.path.join(self.dir, ".watcher")
        os.makedirs(estado_dir, exist_ok=True)
        with open(os.path.join(estado_dir, "qa.lock"), "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "ts": time.time()}, fh)
        codigo, salida = self.correr("qa", "--once")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("lock ocupado", salida)
        self.assertEqual(self.leidas(), [])

    def test_lock_vencido_se_limpia(self):
        self.handoff(hid="h-viejo")
        estado_dir = os.path.join(self.dir, ".watcher")
        os.makedirs(estado_dir, exist_ok=True)
        with open(os.path.join(estado_dir, "qa.lock"), "w", encoding="utf-8") as fh:
            json.dump({"pid": 0, "ts": 0}, fh)
        self.correr("qa", "--once")
        self.assertEqual(self.leidas(), ["h-viejo"])

    def test_sin_comando_bloquea(self):
        self.escribir(config(self.salida, comando=None))
        self.handoff()
        codigo, salida = self.correr("qa", "--once")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("sin comando", salida)

    def test_buzon_inexistente_bloquea(self):
        os.rmdir(self.buzon)
        codigo, salida = self.correr("qa", "--once")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("no existe el buzon", salida)

    def test_modo_tiempo_corre_una_vez_por_intervalo(self):
        self.escribir(config(self.salida, modo="tiempo", desde=(), cada="1h"))
        self.correr("qa", "--once")
        self.correr("qa", "--once")
        self.assertEqual(self.leidas(), ["?"])

    def test_cada_invalido_bloquea(self):
        self.escribir(config(self.salida, modo="tiempo", desde=(), cada="pronto"))
        codigo, salida = self.correr("qa", "--once")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("cada invalido", salida)

    def test_seco_no_ejecuta_ni_recuerda(self):
        self.handoff(hid="h-seco")
        codigo, salida = self.correr("qa", "--seco")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("SECO qa", salida)
        self.assertEqual(self.leidas(), [])
        self.correr("qa", "--once")
        self.assertEqual(self.leidas(), ["h-seco"])

    def test_estado_muestra_pendientes(self):
        self.handoff(hid="h-estado")
        codigo, salida = self.correr("estado", "qa")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("PENDIENTE msg-001.json", salida)
        self.assertIn("h-estado", salida)

    def test_flags_con_valor_no_se_toman_como_roles(self):
        self.handoff(hid="h-flag")
        proc = subprocess.run(
            [sys.executable, WATCHER, "qa", "--once", "--intervalo", "1",
             "--timeout", "5", "--config", self.cfg],
            capture_output=True, text=True, timeout=60)
        salida = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, salida)
        self.assertNotIn("BLOQUEADO 1", salida)
        self.assertEqual(self.leidas(), ["h-flag"])

    def test_humano_no_se_despierta(self):
        codigo, salida = self.correr("usuario", "--once")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("SALTA usuario", salida)


if __name__ == "__main__":
    unittest.main()
