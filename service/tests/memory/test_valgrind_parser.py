"""
Tests del parser de XML de Valgrind — sin Docker, sin subprocesos.
Todos los tests trabajan con strings XML fijos que replican la salida
real de: valgrind --xml=yes --xml-file=out.xml ./programa
"""
import pytest

from app.services.valgrind_parser import (
    ValgrindError,
    ValgrindResult,
    parse_valgrind_xml,
    LEAK_KINDS,
)


# ---------------------------------------------------------------------------
# XML fixtures
# ---------------------------------------------------------------------------

XML_LIMPIO = """<?xml version="1.0"?>
<valgrindoutput>
  <protocolversion>4</protocolversion>
  <protocoltool>memcheck</protocoltool>
  <status><state>FINISHED</state></status>
</valgrindoutput>"""

XML_LEAK_DEFINITIVO = """<?xml version="1.0"?>
<valgrindoutput>
  <error>
    <unique>0x1</unique>
    <tid>1</tid>
    <kind>Leak_DefinitelyLost</kind>
    <xwhat>
      <text>72 bytes in 1 blocks are definitely lost in loss record 1 of 1</text>
      <leakedbytes>72</leakedbytes>
      <leakedblocks>1</leakedblocks>
    </xwhat>
    <stack>
      <frame><ip>0x4C2FB0F</ip><fn>malloc</fn><dir>/usr/lib</dir></frame>
      <frame><ip>0x10001</ip><fn>main</fn><dir>/tmp</dir><file>main.c</file><line>5</line></frame>
    </stack>
  </error>
</valgrindoutput>"""

XML_LEAK_POSIBLE = """<?xml version="1.0"?>
<valgrindoutput>
  <error>
    <unique>0x1</unique>
    <tid>1</tid>
    <kind>Leak_PossiblyLost</kind>
    <xwhat>
      <text>40 bytes in 1 blocks are possibly lost in loss record 1 of 1</text>
      <leakedbytes>40</leakedbytes>
      <leakedblocks>1</leakedblocks>
    </xwhat>
    <stack>
      <frame><ip>0x10001</ip><fn>crear_lista</fn><file>lista.c</file><line>12</line></frame>
    </stack>
  </error>
</valgrindoutput>"""

XML_STILL_REACHABLE = """<?xml version="1.0"?>
<valgrindoutput>
  <error>
    <unique>0x1</unique>
    <tid>1</tid>
    <kind>Leak_StillReachable</kind>
    <xwhat>
      <text>100 bytes in 1 blocks are still reachable in loss record 1 of 1</text>
      <leakedbytes>100</leakedbytes>
      <leakedblocks>1</leakedblocks>
    </xwhat>
    <stack>
      <frame><ip>0x10001</ip><fn>init</fn><file>main.c</file><line>3</line></frame>
    </stack>
  </error>
</valgrindoutput>"""

XML_LECTURA_INVALIDA = """<?xml version="1.0"?>
<valgrindoutput>
  <error>
    <unique>0x2</unique>
    <tid>1</tid>
    <kind>InvalidRead</kind>
    <what>Invalid read of size 4</what>
    <stack>
      <frame><ip>0x10002</ip><fn>procesar</fn><file>utils.c</file><line>20</line></frame>
    </stack>
  </error>
</valgrindoutput>"""

XML_ESCRITURA_INVALIDA = """<?xml version="1.0"?>
<valgrindoutput>
  <error>
    <unique>0x3</unique>
    <tid>1</tid>
    <kind>InvalidWrite</kind>
    <what>Invalid write of size 4</what>
    <stack>
      <frame><ip>0x10003</ip><fn>llenar</fn><file>arreglo.c</file><line>8</line></frame>
    </stack>
  </error>
</valgrindoutput>"""

XML_MULTIPLES_ERRORES = """<?xml version="1.0"?>
<valgrindoutput>
  <error>
    <unique>0x1</unique>
    <tid>1</tid>
    <kind>Leak_DefinitelyLost</kind>
    <xwhat>
      <text>24 bytes in 1 blocks are definitely lost</text>
      <leakedbytes>24</leakedbytes>
      <leakedblocks>1</leakedblocks>
    </xwhat>
    <stack>
      <frame><ip>0x10001</ip><fn>main</fn><file>main.c</file><line>10</line></frame>
    </stack>
  </error>
  <error>
    <unique>0x2</unique>
    <tid>1</tid>
    <kind>Leak_DefinitelyLost</kind>
    <xwhat>
      <text>48 bytes in 2 blocks are definitely lost</text>
      <leakedbytes>48</leakedbytes>
      <leakedblocks>2</leakedblocks>
    </xwhat>
    <stack>
      <frame><ip>0x10002</ip><fn>cargar</fn><file>datos.c</file><line>33</line></frame>
    </stack>
  </error>
  <error>
    <unique>0x3</unique>
    <tid>1</tid>
    <kind>InvalidRead</kind>
    <what>Invalid read of size 8</what>
    <stack>
      <frame><ip>0x10003</ip><fn>leer</fn><file>datos.c</file><line>50</line></frame>
    </stack>
  </error>
</valgrindoutput>"""

XML_SIN_FRAME_CON_ARCHIVO = """<?xml version="1.0"?>
<valgrindoutput>
  <error>
    <unique>0x1</unique>
    <tid>1</tid>
    <kind>InvalidRead</kind>
    <what>Invalid read of size 4</what>
    <stack>
      <frame><ip>0x4C2FB0F</ip><fn>malloc</fn></frame>
      <frame><ip>0x4C30A5C</ip><fn>realloc</fn></frame>
    </stack>
  </error>
</valgrindoutput>"""

XML_MALFORMADO = "<valgrindoutput><error><kind>Leak_DefinitelyLost</kind>"  # tag sin cerrar


# ---------------------------------------------------------------------------
# Tests — parse_valgrind_xml
# ---------------------------------------------------------------------------

class TestParseoBasico:
    def test_sin_errores_retorna_lista_vacia(self):
        result = parse_valgrind_xml(XML_LIMPIO)
        assert isinstance(result, ValgrindResult)
        assert result.errors == []

    def test_xml_malformado_lanza_value_error(self):
        with pytest.raises(ValueError, match="inválido"):
            parse_valgrind_xml(XML_MALFORMADO)

    def test_leak_definitivo_se_parsea_correctamente(self):
        result = parse_valgrind_xml(XML_LEAK_DEFINITIVO)
        assert len(result.errors) == 1
        err = result.errors[0]
        assert err.kind == "Leak_DefinitelyLost"
        assert err.leaked_bytes == 72
        assert err.leaked_blocks == 1
        assert "72 bytes" in err.description

    def test_lectura_invalida_usa_what_en_lugar_de_xwhat(self):
        result = parse_valgrind_xml(XML_LECTURA_INVALIDA)
        err = result.errors[0]
        assert err.kind == "InvalidRead"
        assert err.description == "Invalid read of size 4"
        assert err.leaked_bytes == 0
        assert err.leaked_blocks == 0

    def test_escritura_invalida_sin_bytes_filtrados(self):
        result = parse_valgrind_xml(XML_ESCRITURA_INVALIDA)
        err = result.errors[0]
        assert err.kind == "InvalidWrite"
        assert err.leaked_bytes == 0

    def test_multiples_errores_se_parsean_todos(self):
        result = parse_valgrind_xml(XML_MULTIPLES_ERRORES)
        assert len(result.errors) == 3


class TestExtraccionDeFrame:
    def test_saltea_frames_sin_archivo_y_usa_el_primero_con_archivo(self):
        # XML_LEAK_DEFINITIVO tiene malloc primero (sin <file>), luego main.c
        result = parse_valgrind_xml(XML_LEAK_DEFINITIVO)
        err = result.errors[0]
        assert err.file == "main.c"
        assert err.line == 5
        assert err.function == "main"

    def test_leak_posible_toma_primer_frame(self):
        result = parse_valgrind_xml(XML_LEAK_POSIBLE)
        err = result.errors[0]
        assert err.file == "lista.c"
        assert err.line == 12
        assert err.function == "crear_lista"

    def test_sin_frames_con_archivo_retorna_none(self):
        result = parse_valgrind_xml(XML_SIN_FRAME_CON_ARCHIVO)
        err = result.errors[0]
        assert err.file is None
        assert err.line is None
        assert err.function is None


class TestPropiedadesDeValgrindResult:
    def test_has_errors_false_cuando_limpio(self):
        result = parse_valgrind_xml(XML_LIMPIO)
        assert result.has_errors is False

    def test_has_errors_true_con_leak(self):
        result = parse_valgrind_xml(XML_LEAK_DEFINITIVO)
        assert result.has_errors is True

    def test_has_leaks_true_con_leak_definitivo(self):
        result = parse_valgrind_xml(XML_LEAK_DEFINITIVO)
        assert result.has_leaks is True

    def test_has_leaks_false_con_solo_lectura_invalida(self):
        result = parse_valgrind_xml(XML_LECTURA_INVALIDA)
        assert result.has_leaks is False

    def test_has_leaks_true_con_leak_posible(self):
        result = parse_valgrind_xml(XML_LEAK_POSIBLE)
        assert result.has_leaks is True

    def test_definitely_lost_bytes_suma_solo_definite(self):
        result = parse_valgrind_xml(XML_MULTIPLES_ERRORES)
        # 24 + 48 = 72, el InvalidRead no suma
        assert result.definitely_lost_bytes == 72

    def test_total_leaked_bytes_excluye_still_reachable(self):
        result = parse_valgrind_xml(XML_STILL_REACHABLE)
        # StillReachable no se cuenta en total_leaked_bytes
        assert result.total_leaked_bytes == 0

    def test_total_leaked_bytes_incluye_possibly_lost(self):
        result = parse_valgrind_xml(XML_LEAK_POSIBLE)
        assert result.total_leaked_bytes == 40

    def test_still_reachable_cuenta_en_has_leaks(self):
        # StillReachable sí es un "leak" (aparece en el reporte)
        result = parse_valgrind_xml(XML_STILL_REACHABLE)
        assert result.has_leaks is True


class TestPropiedadesDeValgrindError:
    def test_is_leak_true_para_todos_los_tipos_de_leak(self):
        for kind in LEAK_KINDS:
            err = ValgrindError(kind=kind, description="x")
            assert err.is_leak is True

    def test_is_leak_false_para_invalid_read(self):
        err = ValgrindError(kind="InvalidRead", description="x")
        assert err.is_leak is False

    def test_is_leak_false_para_uninit_value(self):
        err = ValgrindError(kind="UninitValue", description="x")
        assert err.is_leak is False
