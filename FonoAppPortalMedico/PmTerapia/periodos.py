"""
Cálculo de los periodos de un plan de terapia.

Los periodos NO se guardan: se derivan de la fecha de inicio y la periodicidad.

    largo      = 1 | 7 | 15 días
    periodo(n) = [fecha_inicio + n·largo, fecha_inicio + (n+1)·largo)

Un video pertenece al periodo que contiene su fecha de subida. "Cumplió el
periodo n" = hay al menos un video por ejercicio dentro de ese rango. No hay
nada que sincronizar ni que se desfase.

Todo se calcula en ZONA_HORARIA_TERAPIA y no en el TIME_ZONE del proyecto
(UTC): con un plan diario, un video subido a las 22:00 en Chile son las 01:00
UTC del día siguiente, y contarlo en el periodo equivocado es un fallo real.

Son funciones puras sobre fechas, sin tocar la base, para poder probarlas con
fechas fijas.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ZONA_HORARIA_TERAPIA = ZoneInfo('America/Santiago')

# Largo de cada periodicidad, en días. Las claves son las de
# PmPlanTerapia.Periodicidad; se repiten aquí para no importar el modelo desde
# un módulo que debe seguir siendo puro.
DIAS_POR_PERIODICIDAD = {
    'DIARIA': 1,
    'SEMANAL': 7,
    'QUINCENAL': 15,
}


def hoy_en_chile(ahora=None):
    """Fecha de hoy en Chile. 'ahora' se acepta para las pruebas."""
    momento = ahora or datetime.now(tz=ZONA_HORARIA_TERAPIA)
    return momento.astimezone(ZONA_HORARIA_TERAPIA).date()


def fecha_en_chile(momento):
    """Fecha calendario en Chile de un datetime con zona (p. ej. fecha_subida en UTC)."""
    return momento.astimezone(ZONA_HORARIA_TERAPIA).date()


def largo_de(periodicidad):
    return DIAS_POR_PERIODICIDAD[periodicidad]


def numero_de_periodo(fecha_inicio, periodicidad, fecha):
    """
    En qué periodo cae una fecha. Negativo si es anterior al inicio del plan,
    cosa que no debería pasar pero que no conviene ocultar.
    """
    return (fecha - fecha_inicio).days // largo_de(periodicidad)


def rango_de_periodo(fecha_inicio, periodicidad, numero):
    """(primer día, último día) del periodo, ambos inclusive."""
    largo = largo_de(periodicidad)
    primero = fecha_inicio + timedelta(days=numero * largo)
    ultimo = primero + timedelta(days=largo - 1)
    return primero, ultimo


def periodo_actual(fecha_inicio, periodicidad, ahora=None):
    """El periodo que contiene hoy."""
    return numero_de_periodo(fecha_inicio, periodicidad, hoy_en_chile(ahora))


def ultimo_periodo_cerrado(fecha_inicio, periodicidad, ahora=None):
    """
    El último periodo ya terminado, o None si todavía no cerró ninguno. Es el
    que el recordatorio revisa: no tiene sentido reclamar un periodo en curso.
    """
    actual = periodo_actual(fecha_inicio, periodicidad, ahora)
    return actual - 1 if actual >= 1 else None


def periodos_cerrados(fecha_inicio, periodicidad, ahora=None):
    """Todos los periodos ya terminados, del 0 al último cerrado."""
    ultimo = ultimo_periodo_cerrado(fecha_inicio, periodicidad, ahora)
    return list(range(ultimo + 1)) if ultimo is not None else []
