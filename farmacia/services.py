"""Servicios transaccionales para movimientos de inventario."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import FolioConsecutivo, Lote


def generar_folio(prefijo, modelo, campo):
    """Reserva un consecutivo diario sin repetirlo entre solicitudes concurrentes."""
    fecha = timezone.localdate()
    with transaction.atomic():
        try:
            consecutivo = FolioConsecutivo.objects.select_for_update().get(
                tipo=prefijo, fecha=fecha
            )
        except FolioConsecutivo.DoesNotExist:
            try:
                with transaction.atomic():
                    consecutivo = FolioConsecutivo.objects.create(
                        tipo=prefijo, fecha=fecha, ultimo_numero=0
                    )
            except IntegrityError:
                consecutivo = FolioConsecutivo.objects.select_for_update().get(
                    tipo=prefijo, fecha=fecha
                )

        numero = consecutivo.ultimo_numero + 1
        fecha_texto = fecha.strftime('%Y%m%d')
        candidato = f'{prefijo}-{fecha_texto}-{numero:04d}'
        while modelo.objects.filter(**{campo: candidato}).exists():
            numero += 1
            candidato = f'{prefijo}-{fecha_texto}-{numero:04d}'

        consecutivo.ultimo_numero = numero
        consecutivo.save(update_fields=['ultimo_numero'])
        return candidato


def bloquear_lotes(cantidades_por_lote):
    """Bloquea y valida lotes. Debe ejecutarse dentro de atomic()."""
    cantidades = {}
    for lote_id, cantidad in cantidades_por_lote.items():
        cantidad_entera = int(cantidad)
        if cantidad_entera <= 0:
            raise ValidationError("Todas las cantidades deben ser mayores que cero.")
        cantidades[str(lote_id)] = cantidad_entera

    lotes = {
        str(lote.id): lote
        for lote in (
            Lote.objects.select_for_update()
            .select_related('medicamento')
            .filter(id__in=sorted(cantidades))
            .order_by('id')
        )
    }
    faltantes = set(cantidades) - set(lotes)
    if faltantes:
        raise ValidationError(f"Lotes inexistentes: {', '.join(sorted(faltantes))}")

    for lote_id, cantidad in cantidades.items():
        lote = lotes[lote_id]
        if lote.existencia < cantidad:
            raise ValidationError(
                f"Stock insuficiente para {lote.lote_codigo}. "
                f"Disponible: {lote.existencia}, solicitado: {cantidad}."
            )
    return lotes


def descontar_lotes(cantidades_por_lote):
    """Bloquea, valida y descuenta cantidades de lotes concretos."""
    lotes = bloquear_lotes(cantidades_por_lote)
    for lote_id, cantidad in cantidades_por_lote.items():
        lote = lotes[str(lote_id)]
        lote.existencia -= int(cantidad)
        lote.save(update_fields=['existencia'])
    return lotes


def surtir_fefo(medicamento_id, cantidad, lote_preferido_id=None):
    """Descuenta por lote preferido y después FEFO dentro de atomic()."""
    cantidad = int(cantidad)
    if cantidad < 0:
        raise ValidationError("La cantidad surtida no puede ser negativa.")
    if cantidad == 0:
        return None, Decimal('0.00'), []

    lotes = list(
        Lote.objects.select_for_update()
        .filter(medicamento_id=medicamento_id, existencia__gt=0)
        .order_by('fecha_caducidad', 'id')
    )
    if lote_preferido_id:
        lotes.sort(
            key=lambda lote: (
                str(lote.id) != str(lote_preferido_id),
                lote.fecha_caducidad,
                lote.id,
            )
        )

    disponible = sum(lote.existencia for lote in lotes)
    if disponible < cantidad:
        raise ValidationError(
            f"Stock insuficiente. Disponible: {disponible}, solicitado: {cantidad}."
        )

    restante = cantidad
    costo_total = Decimal('0.00')
    asignaciones = []
    for lote in lotes:
        if restante == 0:
            break
        descontado = min(lote.existencia, restante)
        lote.existencia -= descontado
        lote.save(update_fields=['existencia'])
        restante -= descontado
        costo_total += lote.costo_unitario * descontado
        asignaciones.append({'lote': lote, 'cantidad': descontado})

    return asignaciones[0]['lote'], costo_total, asignaciones
