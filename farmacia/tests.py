from django.test import TestCase

class BasicSystemTest(TestCase):
    def test_environment_is_ready(self):
        """
        Prueba básica para asegurar que el entorno de testing
        de Django funciona correctamente.
        """
        self.assertEqual(1 + 1, 2)
