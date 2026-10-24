"""Tests del CLI reparto. Solo stdlib: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

CLI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reparto.py")

BASE = {
    "version": 1,
    "roles": {
        "constructor": {
            "modelo": "x/modelo",
            "entorno": "opencode",
            "cwd": "/tmp",
            "acceso": [{"ruta": "/tmp", "modo": "rw"}],
            "trigger": {"modo": "agente", "desde": ["orquestador"], "cada": None},
            "entrega": ["repo"],
        }
    },
}


def correr(cfg, *args):
    proc = subprocess.run(
        [sys.executable, CLI, *args, "--config", cfg],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


class RepartoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = os.path.join(self.tmp.name, "reparto.json")
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(BASE, fh)

    def tearDown(self):
        self.tmp.cleanup()

    def leer(self):
        with open(self.cfg, encoding="utf-8") as fh:
            return json.load(fh)

    def test_validar_ok(self):
        codigo, salida = correr(self.cfg, "validar")
        self.assertEqual(codigo, 0, salida)

    def test_trigger_invalido(self):
        datos = self.leer()
        datos["roles"]["constructor"]["trigger"]["modo"] = "telepatia"
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        codigo, salida = correr(self.cfg, "validar")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("trigger", salida)

    def test_tiempo_sin_cada(self):
        datos = self.leer()
        datos["roles"]["constructor"]["trigger"] = {"modo": "tiempo", "desde": [], "cada": None}
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        codigo, salida = correr(self.cfg, "validar")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("cada", salida)

    def test_agente_sin_desde_es_aviso(self):
        datos = self.leer()
        datos["roles"]["constructor"]["trigger"] = {"modo": "agente", "desde": [], "cada": None}
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        codigo, salida = correr(self.cfg, "validar")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("AVISO", salida)

    def test_ruta_inexistente_con_flag(self):
        datos = self.leer()
        datos["roles"]["constructor"]["cwd"] = "/ruta/que/no/existe"
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        codigo, _ = correr(self.cfg, "validar")
        self.assertEqual(codigo, 0)
        codigo, salida = correr(self.cfg, "validar", "--rutas")
        self.assertEqual(codigo, 1, salida)

    def test_set_cambia_trigger(self):
        codigo, salida = correr(
            self.cfg, "set", "constructor",
            "--modelo", "y/modelo", "--entorno", "dsh", "--cwd", "/tmp",
            "--trigger", "tiempo", "--cada", "10m",
        )
        self.assertEqual(codigo, 0, salida)
        rol = self.leer()["roles"]["constructor"]
        self.assertEqual(rol["modelo"], "y/modelo")
        self.assertEqual(rol["entorno"], "dsh")
        self.assertEqual(rol["trigger"]["modo"], "tiempo")
        self.assertEqual(rol["trigger"]["cada"], "10m")

    def test_set_crea_rol_nuevo(self):
        codigo, salida = correr(
            self.cfg, "set", "qa",
            "--modelo", "z/modelo", "--entorno", "opencode", "--cwd", "/tmp",
            "--trigger", "usuario",
        )
        self.assertEqual(codigo, 0, salida)
        self.assertIn("qa", self.leer()["roles"])

    def test_acceso_add_y_rm(self):
        codigo, salida = correr(self.cfg, "acceso", "constructor", "add", "/tmp/build", "--modo", "ro")
        self.assertEqual(codigo, 0, salida)
        accesos = self.leer()["roles"]["constructor"]["acceso"]
        self.assertIn({"ruta": "/tmp/build", "modo": "ro"}, accesos)

        codigo, salida = correr(self.cfg, "acceso", "constructor", "rm", "/tmp/build")
        self.assertEqual(codigo, 0, salida)
        accesos = self.leer()["roles"]["constructor"]["acceso"]
        self.assertNotIn({"ruta": "/tmp/build", "modo": "ro"}, accesos)

    def test_acceso_modo_invalido(self):
        codigo, salida = correr(self.cfg, "acceso", "constructor", "add", "/tmp", "--modo", "rwx")
        self.assertEqual(codigo, 1, salida)

    def test_ver_muestra_roles(self):
        codigo, salida = correr(self.cfg, "ver")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("constructor", salida)
        self.assertIn("agente", salida)

    def test_config_inexistente_sale_2(self):
        codigo, salida = correr(os.path.join(self.tmp.name, "nada.json"), "validar")
        self.assertEqual(codigo, 2, salida)

    def test_rol_humano_valido(self):
        datos = self.leer()
        datos["roles"]["usuario"] = {
            "tipo": "humano",
            "modelo": None,
            "entorno": None,
            "cwd": ".",
            "acceso": [{"ruta": ".", "modo": "rw"}],
            "trigger": {"modo": "usuario", "desde": [], "cada": None},
            "entrega": [],
        }
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        codigo, salida = correr(self.cfg, "validar")
        self.assertEqual(codigo, 0, salida)

    def test_rol_humano_con_modelo_es_invalido(self):
        datos = self.leer()
        datos["roles"]["usuario"] = {
            "tipo": "humano",
            "modelo": "x/modelo",
            "entorno": "opencode",
            "cwd": ".",
            "acceso": [],
            "trigger": {"modo": "usuario", "desde": [], "cada": None},
            "entrega": [],
        }
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        codigo, salida = correr(self.cfg, "validar")
        self.assertEqual(codigo, 1, salida)
        self.assertIn("humano", salida)

    def test_rol_humano_con_trigger_agente_es_invalido(self):
        datos = self.leer()
        datos["roles"]["usuario"] = {
            "tipo": "humano",
            "modelo": None,
            "entorno": None,
            "cwd": ".",
            "acceso": [],
            "trigger": {"modo": "agente", "desde": ["constructor"], "cada": None},
            "entrega": [],
        }
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        codigo, salida = correr(self.cfg, "validar")
        self.assertEqual(codigo, 1, salida)

    def test_set_tipo_humano_limpia_modelo_y_entorno(self):
        codigo, salida = correr(self.cfg, "set", "usuario", "--tipo", "humano", "--cwd", ".")
        self.assertEqual(codigo, 0, salida)
        rol = self.leer()["roles"]["usuario"]
        self.assertIsNone(rol["modelo"])
        self.assertIsNone(rol["entorno"])
        self.assertEqual(rol["trigger"]["modo"], "usuario")

    def test_rutas_relativas_se_resuelven_contra_el_config(self):
        # La configuración vive en tmp/, con rutas relativas a ese directorio.
        os.makedirs(os.path.join(self.tmp.name, "proyecto"), exist_ok=True)
        datos = self.leer()
        datos["roles"]["constructor"]["cwd"] = "proyecto"
        datos["roles"]["constructor"]["acceso"] = [{"ruta": "proyecto", "modo": "rw"}]
        with open(self.cfg, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        # Se ejecuta desde otro directorio: debe resolver contra el del config.
        codigo, salida = correr(self.cfg, "validar", "--rutas")
        self.assertEqual(codigo, 0, salida)


if __name__ == "__main__":
    unittest.main()
