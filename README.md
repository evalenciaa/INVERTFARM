# 🏥 INVENTFARM - Sistema de Gestión de Inventario Farmacéutico

Sistema integral de gestión de inventario de medicamentos para instituciones de salud, desarrollado con Django.

## 📋 Características Principales

- ✅ **Gestión de Inventario**: Control completo de medicamentos, lotes y existencias
- ✅ **Solicitudes Colectivas**: Sistema de pedidos para enfermería
- ✅ **Registro de Salidas**: Control de entregas con generación de comprobantes PDF
- ✅ **Reportes y Estadísticas**: Análisis de consumo y alertas de stock
- ✅ **Control de Usuarios**: Sistema de roles y permisos (Administrador, Farmacéutico, Enfermero, Médico)
- ✅ **Alertas CPM**: Notificaciones automáticas de medicamentos por vencer
- ✅ **Carga Masiva**: Importación de datos desde Excel

## 🚀 Tecnologías Utilizadas

- **Backend**: Django 5.2.4, Python 3.12
- **Base de Datos**: MySQL/MariaDB
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Reportes**: ReportLab (PDF), XlsxWriter (Excel)
- **Autenticación**: Django Auth + Permisos personalizados

## 📦 Requisitos Previos

- Python 3.10 o superior
- MySQL 8.0 o superior (o MariaDB 10.5+)
- pip (gestor de paquetes de Python)
- Git

## 🔧 Instalación

# 1. Clonar el repositorio

    ```bash
    git clone https://github.com/evalenciaa/inventfarm.git
    cd inventfarm

### 2. Crear entorno virtual
    bash
    python -m venv venv

    # En Windows:
    venv\Scripts\activate

    # En Linux/Mac:
    source venv/bin/activate


# 3. Instalar dependencias
    bash
    pip install -r requirements.txt

# 4. Configurar variables de entorno
    Copia el archivo de ejemplo y edita con tus valores:

    bash
    cp .env.example .env

    Edita .env con tus credenciales:

    text
    DB_NAME=INVENTFARM
    DB_USER=root
    DB_PASSWORD=tu_contraseña_mysql
    DB_HOST=localhost
    DB_PORT=3306

    SECRET_KEY=tu-clave-secreta-generada
    DEBUG=True
    ALLOWED_HOSTS=localhost,127.0.0.1

    EMAIL_HOST_USER=tu_email@gmail.com
    EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicacion
    Generar SECRET_KEY:

    bash
    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 5. Crear base de datos
    bash
    # Entra a MySQL
    mysql -u root -p

    # Crea la base de datos
    CREATE DATABASE INVENTFARM CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    EXIT;

# 6. Ejecutar migraciones
    bash
    python manage.py makemigrations
    python manage.py migrate

# 7. Crear superusuario
    bash
    python manage.py createsuperuser

# 8. Cargar datos iniciales (opcional)
    bash
    python manage.py crear_grupos_y_permisos

# 9. Ejecutar servidor
    bash
    python manage.py runserver
    Accede a: http://localhost:8000

👥 Roles y Permisos
El sistema cuenta con los siguientes roles:

        Rol	                                Permisos
    Administrador	          Acceso total al sistema, gestión de usuarios
    Jefe de Farmacia	      Gestión de inventario, reportes, carga masiva
    Farmacéutico	          Registro de salidas, consulta de inventario
    Jefe de Enfermería	      Crear solicitudes colectivas
    Enfermero	              Crear solicitudes colectivas
    Médico	                  Consulta de inventario (solo lectura)

🔐 Seguridad
    Las contraseñas se almacenan usando PBKDF2

    Sesiones expiran después de 1 hora de inactividad

    Protección CSRF en todos los formularios

    Permisos granulares por módulo

📊 Módulos del Sistema
    Inventario
        Gestión de medicamentos y lotes

        Control de existencias y fechas de vencimiento

        Alertas automáticas de stock bajo

    Salidas
        Registro de entregas de medicamentos

        Generación de comprobantes PDF

        Historial de transacciones

    Colectivos (Enfermería)
        Solicitudes de medicamentos por servicio

        Aprobación/rechazo de solicitudes

        Surtido parcial o total

    Reportes
        Consumo por medicamento

        Estadísticas de salidas

        Exportación a Excel/PDF

    Administración
        Gestión de usuarios y roles

        Asignación de permisos

        Configuración del sistema

🛠️ Comandos Útiles
    bash
    # Crear migraciones
    python manage.py makemigrations

    # Aplicar migraciones
    python manage.py migrate

    # Crear superusuario
    python manage.py createsuperuser

    # Recopilar archivos estáticos (para producción)
    python manage.py collectstatic

    # Ejecutar tests
    python manage.py test

📝 Notas Adicionales
    Configuración de Email (Gmail)
        Para las notificaciones de alertas CPM:
        Ve a tu cuenta de Google
        Activa "Verificación en 2 pasos"
        Genera una "Contraseña de aplicación"
        Usa esa contraseña en EMAIL_HOST_PASSWORD

    Base de Datos en Producción
        Para producción, considera usar PostgreSQL en lugar de MySQL.

🐛 Solución de Problemas
    Error: No module named 'pymysql'
        bash
        pip install pymysql
    
    Error: Access denied for user 'root'@'localhost'
        Verifica tus credenciales en .env

    Error: SECRET_KEY not found
        Asegúrate de tener el archivo .env con todas las variables

📄 Licencia
Este proyecto es privado y de uso interno.

👨‍💻 Autor
Desarrollado por Eliu J. Valencia Azamar

📧 Contacto
Para soporte o consultas: iinf22.evalenciaa@itesco.edu.mx

¡Gracias por usar INVENTFARM! 🚀
