import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.models.schemas import CompilationResult


PROMPT_TEMPLATE = """
Sos un profesor de la materia Algoritmos y Estructuras de Datos que corrige entregas de alumnos escritas en C.

## Consigna de la entrega:
{consigna}

## Código del alumno:
{codigo}

{seccion_compilacion}

## Tu tarea:
Analizá el código y generá un feedback detallado que incluya:
1. Si cumple con lo pedido en la consigna (justificá)
2. Qué está bien hecho
3. Qué le falta o está mal
{punto_compilacion}
5. Una lista de los ítems de la consigna que NO se cumplieron

Importante:
- Evaluá únicamente lo que se puede verificar leyendo el código fuente. Ignorá requisitos que no son verificables desde el código, como entrega de videos, subida al campus, presentaciones orales, etc.
- Antes de afirmar que algo "no se usa" o "no se implementa", revisá si existe un typedef que lo defina con otro nombre. Por ejemplo, si la consigna pide "puntero a void" y el alumno define `typedef void * DatoPtr` y usa `DatoPtr` en todo el código, eso SÍ cumple el requisito — es un puntero a void con un alias. No penalices el uso correcto de typedef.

Respondé en español, de forma clara y constructiva.
"""

SECCION_COMPILACION = """## Resultado de compilación:
- Compiló correctamente: {compilo}
- Errores: {errores}
- Warnings: {warnings}"""


def analyze_submission(consigna: str, c_files: list[str], compilation: CompilationResult, con_compilacion: bool = True) -> tuple[str, list[str]]:
    """
    Manda el código y resultado de compilación al LLM.
    Retorna (feedback_texto, items_faltantes).
    """
    codigo = ""
    for path in c_files:
        filename = os.path.basename(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            codigo += f"// === {filename} ===\n{f.read()}\n\n"

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    chain = prompt | llm

    if con_compilacion:
        seccion_compilacion = SECCION_COMPILACION.format(
            compilo="Sí" if compilation.success else "No",
            errores="\n".join(compilation.errors) if compilation.errors else "Ninguno",
            warnings="\n".join(compilation.warnings) if compilation.warnings else "Ninguno",
        )
        punto_compilacion = "4. Explicación de cada warning/error en términos simples para un estudiante"
    else:
        seccion_compilacion = ""
        punto_compilacion = "4. Evaluá si el código parece correcto estructuralmente aunque no se haya compilado"

    response = chain.invoke({
        "consigna": consigna,
        "codigo": codigo,
        "seccion_compilacion": seccion_compilacion,
        "punto_compilacion": punto_compilacion,
    })

    feedback = response.content

    # Extrae items faltantes del feedback (mejorar con structured output a futuro)
    items_faltantes = []
    for line in feedback.splitlines():
        if line.strip().startswith("-") and ("falta" in line.lower() or "no se" in line.lower()):
            items_faltantes.append(line.strip("- ").strip())

    return feedback, items_faltantes
