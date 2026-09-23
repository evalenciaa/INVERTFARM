import calendar
import math

from django.db.models import Sum
from django.utils import timezone

from .models import CPMMedicamento, Medicamento, RecetaMedicamento


MESES_EVALUADOS = 3


def restar_meses(fecha, meses):
    """Desplaza una fecha conservando el día cuando existe en el mes destino."""
    indice_mes = fecha.year * 12 + fecha.month - 1 - meses
    anio, mes_cero = divmod(indice_mes, 12)
    mes = mes_cero + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


def periodo_cpm(fecha_referencia=None):
    """Devuelve la ventana móvil de tres meses usada por el CPM."""
    fin = fecha_referencia or timezone.localdate()
    return restar_meses(fin, MESES_EVALUADOS), fin


def consumo_tres_meses(medicamento_id, fecha_referencia=None):
    inicio, fin = periodo_cpm(fecha_referencia)
    total = RecetaMedicamento.objects.filter(
        medicamento_id=medicamento_id,
        receta__fecha_surtido__gt=inicio,
        receta__fecha_surtido__lte=fin,
        cantidad_surtida__gt=0,
    ).aggregate(total=Sum('cantidad_surtida'))['total']
    return total or 0


def calcular_cpm_medicamento(medicamento_id, fecha_referencia=None):
    """Calcula el promedio mensual; se redondea hacia arriba a unidades enteras."""
    total = consumo_tres_meses(medicamento_id, fecha_referencia)
    return math.ceil(total / MESES_EVALUADOS)


def actualizar_cpm_medicamento(medicamento_id, fecha_referencia=None):
    valor = calcular_cpm_medicamento(medicamento_id, fecha_referencia)
    cpm, _ = CPMMedicamento.objects.update_or_create(
        medicamento_id=medicamento_id,
        defaults={'valor': valor, 'actualizado_por': None},
    )
    return cpm


def actualizar_todos_los_cpm(fecha_referencia=None):
    """Sincroniza el CPM calculado de todo el catálogo de medicamentos."""
    actualizados = 0
    for medicamento_id in Medicamento.objects.values_list('id', flat=True).iterator():
        actualizar_cpm_medicamento(medicamento_id, fecha_referencia)
        actualizados += 1
    return actualizados


def calcular_estado_inventario(existencia, cpm):
    """Calcula stock máximo, excedente, porcentaje y estado del medicamento."""
    existencia = max(int(existencia or 0), 0)
    cpm = max(int(cpm or 0), 0)
    stock_maximo = (cpm * 2) + 10
    excedente = max(existencia - stock_maximo, 0)
    porcentaje = round((existencia / stock_maximo) * 100, 1)

    if existencia == 0:
        estado = 'desabasto'
    elif existencia < cpm:
        estado = 'bajo'
    elif existencia <= stock_maximo:
        estado = 'adecuado'
    else:
        estado = 'excedente'

    return {
        'estado': estado,
        'stock_maximo': stock_maximo,
        'excedente': excedente,
        'porcentaje': porcentaje,
    }
