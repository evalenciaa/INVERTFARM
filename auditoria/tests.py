from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from auditoria.models import Bitacora
from auditoria.services import registrar_evento
from farmacia.models import CatalogoAntibioticosWHO, Medicamento


class AuditoriaTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='auditor', password='ContrasenaSegura123!', rol='FARMACIA',
        )
        Bitacora.objects.all().delete()

    def test_cambio_operativo_registra_valores_anteriores_y_nuevos(self):
        medicamento = Medicamento.objects.create(clave='AUD-001', descripcion='Prueba auditoría')
        Bitacora.objects.all().delete()

        medicamento.descripcion = 'Prueba modificada'
        medicamento.save()

        registro = Bitacora.objects.get(accion='EDITAR', modelo_afectado='Medicamento')
        self.assertEqual(registro.detalles['descripcion']['antes'], 'Prueba auditoría')
        self.assertEqual(registro.detalles['descripcion']['despues'], 'Prueba modificada')

    def test_nunca_guarda_contrasenas_ni_tokens_en_detalles(self):
        registro = registrar_evento(
            'EDITAR', 'Prueba', detalles={
                'password': 'secreto', 'new_password': 'otro-secreto',
                'refresh_token': 'token-secreto', 'valor': 'conservar',
            }, usuario=self.usuario,
        )

        self.assertEqual(registro.detalles['password'], '[REDACTADO]')
        self.assertEqual(registro.detalles['new_password'], '[REDACTADO]')
        self.assertEqual(registro.detalles['refresh_token'], '[REDACTADO]')
        self.assertEqual(registro.detalles['valor'], 'conservar')

    def test_catalogo_who_tambien_deja_evidencia_de_sus_cambios(self):
        catalogo = CatalogoAntibioticosWHO.objects.create(
            codigo_atc='J01AA01', categoria_aware='Access', valor_atc='1.0000',
        )

        registro = Bitacora.objects.get(
            accion='CREAR', modelo_afectado='CatalogoAntibioticosWHO',
            id_objeto=str(catalogo.pk),
        )
        self.assertEqual(registro.detalles['evento'], 'registro_creado')

    def test_inicio_y_fallo_de_sesion_quedan_registrados_con_contexto(self):
        respuesta = self.client.post(reverse('login'), {
            'username': self.usuario.username,
            'password': 'incorrecta',
        })
        self.assertEqual(respuesta.status_code, 200)
        fallido = Bitacora.objects.get(accion='FALLO_ACCESO')
        self.assertEqual(fallido.usuario_texto, self.usuario.username)
        self.assertEqual(fallido.ruta, reverse('login'))
        self.assertEqual(fallido.metodo, 'POST')
        self.assertTrue(fallido.correlacion_id)

        Bitacora.objects.all().delete()
        respuesta = self.client.post(reverse('login'), {
            'username': self.usuario.username,
            'password': 'ContrasenaSegura123!',
        })
        self.assertEqual(respuesta.status_code, 302)
        exitoso = Bitacora.objects.get(accion='ACCESO')
        self.assertEqual(exitoso.usuario, self.usuario)
        self.assertEqual(exitoso.ruta, reverse('login'))

    def test_cambios_de_grupo_del_usuario_quedan_registrados(self):
        grupo = Group.objects.create(name='Grupo de prueba auditoría')
        Bitacora.objects.all().delete()

        self.usuario.groups.add(grupo)

        registro = Bitacora.objects.get(
            accion='EDITAR', modelo_afectado='UsuarioPersonalizado',
        )
        self.assertEqual(registro.detalles['campo'], 'grupos')
        self.assertEqual(registro.detalles['operacion'], 'post_add')
        self.assertEqual(registro.detalles['valores'], [grupo.name])

    def test_bitacora_no_admite_altas_ni_ediciones_en_admin(self):
        administrador = get_user_model().objects.create_superuser(
            username='ti', password='ContrasenaSegura123!', email='ti@example.com', rol='PENDIENTE',
        )
        self.client.force_login(administrador)
        self.assertEqual(self.client.get(reverse('admin:auditoria_bitacora_add')).status_code, 403)

    def test_sesion_se_configura_para_expirar_a_los_veinte_minutos_de_inactividad(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 20 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
