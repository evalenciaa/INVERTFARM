from datetime import date, timedelta

from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from farmacia.models import (
    Lote, Medicamento, Paciente, Presentacion, Receta,
    UsuarioPersonalizado,
)

from .models import Colectivo, ColectivoMedicamento


class FlujoColectivosTests(TestCase):
    def setUp(self):
        self.grupo_farmacia = Group.objects.create(name='Farmacéutico')
        self.grupo_enfermeria = Group.objects.create(name='Enfermero')
        self.farmaceutico = UsuarioPersonalizado.objects.create_user(
            username='farmacia', password='PruebaSegura123!', rol='FARMACIA'
        )
        self.farmaceutico.groups.add(self.grupo_farmacia)
        self.farmaceutico.user_permissions.add(*Permission.objects.filter(
            codename__in=['view_colectivo', 'respond_colectivo', 'complete_colectivo']
        ))
        self.enfermero = UsuarioPersonalizado.objects.create_user(
            username='enfermero', password='PruebaSegura123!', rol='ENFERMERIA'
        )
        self.enfermero.groups.add(self.grupo_enfermeria)
        self.enfermero.user_permissions.add(*Permission.objects.filter(
            codename__in=['view_colectivo', 'change_colectivo', 'create_colectivo']
        ))
        self.otro_enfermero = UsuarioPersonalizado.objects.create_user(
            username='otro_enfermero', password='PruebaSegura123!', rol='ENFERMERIA'
        )
        self.otro_enfermero.groups.add(self.grupo_enfermeria)
        self.otro_enfermero.user_permissions.add(Permission.objects.get(codename='view_colectivo'))
        self.paciente = Paciente.objects.create(
            nombre_completo='Paciente Colectivo', curp='COLEPRUEBA12345678',
            fecha_nacimiento=date(1985, 1, 1)
        )
        self.presentacion = Presentacion.objects.create(nombre='UNIDAD', unidades_por_caja=1)
        self.medicamento = Medicamento.objects.create(
            clave='010.000.0200', descripcion='Medicamento colectivo',
            presentacion=self.presentacion
        )
        self.lote = Lote.objects.create(
            id='LOT-COLECTIVO', medicamento=self.medicamento,
            lote_codigo='COL-001', fecha_caducidad=date.today() + timedelta(days=180),
            existencia=10, presentacion=self.presentacion, costo_unitario='5.00'
        )
        self.colectivo = Colectivo.objects.create(
            tipo_colectivo='PACIENTE', paciente=self.paciente,
            numero_cama='C-01', servicio='Urgencias',
            enfermero_solicitante=self.enfermero, estado='EN_REVISION'
        )
        self.item = ColectivoMedicamento.objects.create(
            colectivo=self.colectivo, medicamento=self.medicamento,
            cantidad_solicitada=4
        )

    def test_enfermero_solo_puede_ver_sus_colectivos(self):
        self.client.force_login(self.otro_enfermero)
        response = self.client.get(
            reverse('detalle_colectivo_enfermeria', args=[self.colectivo.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_flujo_responder_y_completar_descuenta_inventario(self):
        self.client.force_login(self.farmaceutico)
        response = self.client.post(
            reverse('responder_colectivo', args=[self.colectivo.id]),
            {
                f'disponible_{self.item.id}': 'on',
                f'comentario_{self.item.id}': 'Disponible',
                'respuesta_farmacia': 'Puede surtirse',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'RESPONDIDO')

        response = self.client.post(
            reverse('completar_colectivo', args=[self.colectivo.id]),
            {
                f'cantidad_surtida_{self.item.id}': '4',
                f'lote_id_{self.item.id}': self.lote.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'COMPLETADO')
        self.assertEqual(self.lote.existencia, 6)
        self.assertTrue(Receta.objects.filter(id_folio=self.colectivo.folio).exists())

        self.medicamento.descripcion = 'Medicamento colectivo ' + ('X' * 500)
        self.medicamento.save(update_fields=['descripcion'])
        pdf = self.client.get(reverse('generar_pdf_colectivo', args=[self.colectivo.id]))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertNotIn(b'X' * 250, pdf.content)

    def test_confirmar_directamente_en_revision_descuenta_inventario(self):
        self.client.force_login(self.farmaceutico)

        response = self.client.post(
            reverse('completar_colectivo', args=[self.colectivo.id]),
            {
                f'cantidad_surtida_{self.item.id}': '4',
                f'lote_id_{self.item.id}': self.lote.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.item.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'COMPLETADO')
        self.assertTrue(self.item.disponible)
        self.assertEqual(self.lote.existencia, 6)

    def test_no_se_puede_completar_dos_veces(self):
        self.colectivo.estado = 'COMPLETADO'
        self.colectivo.save(update_fields=['estado'])
        self.client.force_login(self.farmaceutico)
        response = self.client.post(
            reverse('completar_colectivo', args=[self.colectivo.id]),
            {f'cantidad_surtida_{self.item.id}': '4'},
        )
        self.assertEqual(response.status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.existencia, 10)

    def test_no_se_completa_antes_de_responder_la_revision(self):
        self.client.force_login(self.farmaceutico)
        response = self.client.post(
            reverse('completar_colectivo', args=[self.colectivo.id]),
            {f'cantidad_surtida_{self.item.id}': '4'},
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'EN_REVISION')
        self.assertEqual(self.lote.existencia, 10)
        self.assertFalse(Receta.objects.filter(id_folio=self.colectivo.folio).exists())

    def test_stock_insuficiente_editar_agregar_revisar_y_completar(self):
        self.item.cantidad_solicitada = 12
        self.item.save(update_fields=['cantidad_solicitada'])
        alternativa = Medicamento.objects.create(
            clave='010.000.0201', descripcion='Medicamento alternativo',
            presentacion=self.presentacion,
        )
        lote_alternativa = Lote.objects.create(
            id='LOT-ALTERNATIVA', medicamento=alternativa,
            lote_codigo='COL-002', fecha_caducidad=date.today() + timedelta(days=240),
            existencia=10, presentacion=self.presentacion, costo_unitario='7.00',
        )

        self.client.force_login(self.farmaceutico)
        response = self.client.post(
            reverse('responder_colectivo', args=[self.colectivo.id]),
            {
                f'comentario_{self.item.id}': 'Stock insuficiente',
                'respuesta_farmacia': 'Ajustar cantidad o agregar alternativa',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'RESPONDIDO')
        self.assertFalse(self.item.disponible)

        self.client.force_login(self.enfermero)
        detalle = self.client.get(
            reverse('detalle_colectivo_enfermeria', args=[self.colectivo.id])
        )
        self.assertContains(detalle, 'value="12"', html=False)
        response = self.client.post(
            reverse('editar_colectivo', args=[self.colectivo.id]),
            {
                'medicamento_id[]': [str(self.medicamento.id), str(alternativa.id)],
                'cantidad[]': ['5', '3'],
                'observaciones': 'Se redujo la cantidad y se agregó una alternativa.',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'PENDIENTE')
        self.assertIsNone(self.colectivo.farmaceutico_asignado)
        self.assertEqual(self.colectivo.medicamentos.count(), 2)
        self.assertEqual(self.item.cantidad_solicitada, 5)
        self.assertTrue(self.item.disponible)
        self.assertEqual(self.item.comentario_farmacia, '')

        self.client.force_login(self.farmaceutico)
        response = self.client.get(
            reverse('detalle_colectivo_farmacia', args=[self.colectivo.id])
        )
        self.assertEqual(response.status_code, 200)
        self.colectivo.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'EN_REVISION')
        self.assertContains(response, 'id="btn-confirmar-surtido"', html=False)
        self.assertContains(response, 'id="modal-confirmar-surtido"', html=False)

        item_alternativa = self.colectivo.medicamentos.get(medicamento=alternativa)
        response = self.client.post(
            reverse('responder_colectivo', args=[self.colectivo.id]),
            {
                f'disponible_{self.item.id}': 'on',
                f'disponible_{item_alternativa.id}': 'on',
                'respuesta_farmacia': 'Ambos disponibles',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'RESPONDIDO')

        response = self.client.post(
            reverse('completar_colectivo', args=[self.colectivo.id]),
            {
                f'cantidad_surtida_{self.item.id}': '5',
                f'lote_id_{self.item.id}': self.lote.id,
                f'cantidad_surtida_{item_alternativa.id}': '3',
                f'lote_id_{item_alternativa.id}': lote_alternativa.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.lote.refresh_from_db()
        lote_alternativa.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'COMPLETADO')
        self.assertEqual(self.lote.existencia, 5)
        self.assertEqual(lote_alternativa.existencia, 7)
        self.assertEqual(
            Receta.objects.get(id_folio=self.colectivo.folio).recetamedicamento_set.count(),
            2,
        )

    def test_medicamento_invalido_no_borra_los_renglones_actuales(self):
        self.colectivo.estado = 'RESPONDIDO'
        self.colectivo.save(update_fields=['estado'])
        self.client.force_login(self.enfermero)
        response = self.client.post(
            reverse('editar_colectivo', args=[self.colectivo.id]),
            {
                'medicamento_id[]': [str(self.medicamento.id), '999999'],
                'cantidad[]': ['4', '2'],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'RESPONDIDO')
        self.assertEqual(self.colectivo.medicamentos.count(), 1)
        self.assertTrue(
            self.colectivo.medicamentos.filter(pk=self.item.pk, cantidad_solicitada=4).exists()
        )

    def test_busqueda_de_colectivos_excluye_antibioticos_y_codigos_atc(self):
        antibiotico = Medicamento.objects.create(
            clave='010.000.0300', descripcion='Antibiótico marcado',
            presentacion=self.presentacion, es_antibiotico=True,
        )
        con_atc = Medicamento.objects.create(
            clave='010.000.0301', descripcion='Medicamento con ATC',
            presentacion=self.presentacion, codigo_atc='J01CA04',
        )
        permitido = Medicamento.objects.create(
            clave='010.000.0302', descripcion='Medicamento permitido',
            presentacion=self.presentacion, es_antibiotico=False, codigo_atc='',
        )

        self.client.force_login(self.enfermero)
        response = self.client.get(reverse('api_buscar_medicamentos'), {'q': '010'})
        self.assertEqual(response.status_code, 200)
        ids = {resultado['id'] for resultado in response.json()['results']}
        self.assertIn(permitido.id, ids)
        self.assertNotIn(antibiotico.id, ids)
        self.assertNotIn(con_atc.id, ids)

        pagina = self.client.get(reverse('crear_colectivo'))
        medicamentos = set(pagina.context['medicamentos'])
        self.assertIn(permitido, medicamentos)
        self.assertNotIn(antibiotico, medicamentos)
        self.assertNotIn(con_atc, medicamentos)

    def test_servidor_rechaza_antibiotico_en_creacion_y_edicion(self):
        antibiotico = Medicamento.objects.create(
            clave='010.000.0400', descripcion='Antibiótico restringido',
            presentacion=self.presentacion, es_antibiotico=True,
        )
        self.client.force_login(self.enfermero)
        response = self.client.post(reverse('crear_colectivo'), {
            'tipo_colectivo': 'PACIENTE',
            'paciente': self.paciente.id,
            'numero_cama': 'C-02',
            'servicio': 'Urgencias',
            'medicamento_id[]': [str(antibiotico.id)],
            'cantidad[]': ['2'],
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no permiten medicamentos antibióticos')
        self.assertEqual(Colectivo.objects.count(), 1)

        self.colectivo.estado = 'RESPONDIDO'
        self.colectivo.save(update_fields=['estado'])
        response = self.client.post(
            reverse('editar_colectivo', args=[self.colectivo.id]),
            {
                'medicamento_id[]': [str(self.medicamento.id), str(antibiotico.id)],
                'cantidad[]': ['4', '2'],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.colectivo.refresh_from_db()
        self.assertEqual(self.colectivo.estado, 'RESPONDIDO')
        self.assertEqual(self.colectivo.medicamentos.count(), 1)
        self.assertTrue(self.colectivo.medicamentos.filter(medicamento=self.medicamento).exists())

    def test_modulo_antibioticos_filtra_y_crea_solo_medicamentos_permitidos(self):
        antibiotico = Medicamento.objects.create(
            clave='010.000.0500', descripcion='Antibiótico por marca',
            presentacion=self.presentacion, es_antibiotico=True,
        )
        con_atc = Medicamento.objects.create(
            clave='010.000.0501', descripcion='Antibiótico por ATC',
            presentacion=self.presentacion, codigo_atc='J01CA04',
        )
        self.client.force_login(self.enfermero)

        principal = self.client.get(reverse('enfermeria_principal'))
        self.assertContains(principal, 'Colectivo de Antibióticos')

        response = self.client.get(
            reverse('api_buscar_medicamentos_antibioticos'), {'q': '010'}
        )
        ids = {resultado['id'] for resultado in response.json()['results']}
        self.assertIn(antibiotico.id, ids)
        self.assertIn(con_atc.id, ids)
        self.assertNotIn(self.medicamento.id, ids)

        response = self.client.post(reverse('crear_colectivo_antibioticos'), {
            'tipo_colectivo': 'PACIENTE',
            'paciente': self.paciente.id,
            'numero_cama': 'C-03',
            'servicio': 'Urgencias',
            'medicamento_id[]': [str(antibiotico.id), str(con_atc.id)],
            'cantidad[]': ['2', '1'],
        })
        nuevo = Colectivo.objects.exclude(pk=self.colectivo.pk).get()
        self.assertRedirects(
            response, reverse('detalle_colectivo_antibioticos', args=[nuevo.id])
        )
        self.assertEqual(nuevo.medicamentos.count(), 2)

        lista_antibioticos = self.client.get(reverse('lista_colectivos_antibioticos'))
        self.assertContains(lista_antibioticos, nuevo.folio)
        self.assertNotContains(lista_antibioticos, self.colectivo.folio)
        lista_general = self.client.get(reverse('lista_colectivos_enfermeria'))
        self.assertNotContains(lista_general, nuevo.folio)
        self.assertContains(lista_general, self.colectivo.folio)

        detalle = self.client.get(reverse('detalle_colectivo_antibioticos', args=[nuevo.id]))
        self.assertNotContains(detalle, 'Descargar PDF')

        nuevo.estado = 'COMPLETADO'
        nuevo.save(update_fields=['estado'])
        detalle = self.client.get(reverse('detalle_colectivo_antibioticos', args=[nuevo.id]))
        self.assertContains(detalle, 'Descargar PDF')
        response = self.client.get(
            reverse('generar_pdf_colectivo_antibioticos', args=[nuevo.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_modulo_antibioticos_rechaza_medicamento_general(self):
        self.client.force_login(self.enfermero)
        response = self.client.post(reverse('crear_colectivo_antibioticos'), {
            'tipo_colectivo': 'PACIENTE',
            'paciente': self.paciente.id,
            'numero_cama': 'C-04',
            'servicio': 'Urgencias',
            'medicamento_id[]': [str(self.medicamento.id)],
            'cantidad[]': ['2'],
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'solo permite medicamentos marcados como')
        self.assertEqual(Colectivo.objects.count(), 1)

    def test_farmacia_procesa_colectivo_antibioticos_en_modulo_separado(self):
        descripcion_larga = 'Antibiótico para surtir ' + ('Y' * 500)
        antibiotico = Medicamento.objects.create(
            clave='010.000.0600', descripcion=descripcion_larga,
            presentacion=self.presentacion, es_antibiotico=True,
            categoria_aware='Access', codigo_atc='J01CA04',
        )
        lote_antibiotico = Lote.objects.create(
            id='LOT-ANTIBIOTICO', medicamento=antibiotico,
            lote_codigo='ANT-001', fecha_caducidad=date.today() + timedelta(days=120),
            existencia=8, presentacion=self.presentacion, costo_unitario='9.00',
        )
        colectivo_antibiotico = Colectivo.objects.create(
            tipo_colectivo='PACIENTE', paciente=self.paciente,
            numero_cama='C-05', servicio='Urgencias',
            enfermero_solicitante=self.enfermero, estado='PENDIENTE',
        )
        item_antibiotico = ColectivoMedicamento.objects.create(
            colectivo=colectivo_antibiotico, medicamento=antibiotico,
            cantidad_solicitada=3,
        )
        self.client.force_login(self.farmaceutico)

        lista_general = self.client.get(reverse('lista_colectivos_farmacia'))
        self.assertNotContains(lista_general, colectivo_antibiotico.folio)
        lista_antibioticos = self.client.get(
            reverse('lista_colectivos_antibioticos_farmacia')
        )
        self.assertContains(lista_antibioticos, colectivo_antibiotico.folio)
        self.assertNotContains(lista_antibioticos, self.colectivo.folio)
        busqueda = self.client.get(
            reverse('lista_colectivos_antibioticos_farmacia'),
            {'q': self.paciente.nombre_completo},
        )
        self.assertContains(busqueda, colectivo_antibiotico.folio)

        acceso_cruzado = self.client.get(
            reverse('detalle_colectivo_farmacia', args=[colectivo_antibiotico.id])
        )
        self.assertEqual(acceso_cruzado.status_code, 404)
        detalle = self.client.get(
            reverse('detalle_colectivo_antibioticos_farmacia', args=[colectivo_antibiotico.id])
        )
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, 'Detalle del Colectivo de Antibióticos')
        colectivo_antibiotico.refresh_from_db()
        self.assertEqual(colectivo_antibiotico.estado, 'EN_REVISION')

        response = self.client.post(
            reverse('responder_colectivo_antibioticos', args=[colectivo_antibiotico.id]),
            {
                f'disponible_{item_antibiotico.id}': 'on',
                'respuesta_farmacia': 'Antibiótico disponible',
            },
        )
        self.assertRedirects(response, reverse('lista_colectivos_antibioticos_farmacia'))
        colectivo_antibiotico.refresh_from_db()
        self.assertEqual(colectivo_antibiotico.estado, 'RESPONDIDO')

        response = self.client.post(
            reverse('completar_colectivo_antibioticos', args=[colectivo_antibiotico.id]),
            {
                f'cantidad_surtida_{item_antibiotico.id}': '3',
                f'lote_id_{item_antibiotico.id}': lote_antibiotico.id,
            },
        )
        self.assertRedirects(response, reverse('lista_colectivos_antibioticos_farmacia'))
        colectivo_antibiotico.refresh_from_db()
        lote_antibiotico.refresh_from_db()
        self.assertEqual(colectivo_antibiotico.estado, 'COMPLETADO')
        self.assertEqual(lote_antibiotico.existencia, 5)

        detalle_completado = self.client.get(
            reverse('detalle_colectivo_antibioticos_farmacia', args=[colectivo_antibiotico.id])
        )
        self.assertContains(detalle_completado, 'Descargar PDF')

        pdf = self.client.get(
            reverse('generar_pdf_colectivo_antibioticos', args=[colectivo_antibiotico.id])
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertIn(
            f'Colectivo_Antibioticos_{colectivo_antibiotico.folio}.pdf',
            pdf['Content-Disposition'],
        )
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertIn(b'Colectivo de Antibi', pdf.content)
        self.assertIn(b'J01CA04', pdf.content)
        self.assertIn(b'Access', pdf.content)
        self.assertNotIn(b'Y' * 250, pdf.content)
