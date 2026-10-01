# Operación de respaldos en Windows Server

Este procedimiento completa la protección P1 de INVENTFARM. Debe realizarlo
personal de TI directamente en el Windows Server, no desde una estación de
trabajo de usuarios.

## 1. Cuenta de servicio y rutas

1. Cree una cuenta local o de dominio sin privilegios de administrador, por
   ejemplo `DOMINIO\svc_inventfarm_backup`.
2. Cree el volumen local cifrado `D:\Inventfarm\Backups` y un recurso externo,
   por ejemplo `\\NAS-SALUD\InventfarmBackups`.
3. Otorgue a la cuenta de servicio **Modificar** únicamente sobre:
   - La carpeta del proyecto y `logs` (lectura y escritura de bitácora).
   - `D:\Inventfarm\Backups`.
   - El recurso externo de respaldos.
4. No conceda acceso a `Users`, `Everyone`, cuentas de usuarios clínicos ni
   acceso administrativo a la cuenta de servicio.

La aplicación web también debe ejecutarse con una cuenta que pueda escribir en
la copia local. No use una cuenta administradora de Windows para el servicio
web ni para la tarea programada.

## 2. Variables de entorno

Agregue estas variables al `.env` del servidor. Las rutas se muestran como
ejemplo y deben coincidir con la infraestructura aprobada por TI:

```env
BACKUP_STORAGE_DIR=D:\Inventfarm\Backups
BACKUP_REMOTE_DIRECTORY=\\NAS-SALUD\InventfarmBackups
BACKUP_REMOTE_REQUIRED=True
BACKUP_ALLOW_SAME_VOLUME=False
BACKUP_LOCAL_RETENTION=10
BACKUP_REMOTE_RETENTION=30
BACKUP_MIN_FREE_GB=5
BACKUP_ALERT_RECIPIENTS=ti@institucion.gob.mx
```

`BACKUP_REMOTE_REQUIRED=True` hace que una copia programada sea considerada
fallida si no llega al destino externo; la copia local se conserva y el error
queda en bitácora y correo. El recurso externo debe estar en otro volumen o
servidor, nunca en una subcarpeta del proyecto ni del mismo disco.

Conserve una copia cifrada y restringida de `.env`, especialmente de
`SECRET_KEY`. Las copias verificables usan esa clave para validar el manifiesto;
no debe rotarse ni perderse sin un plan de recuperación.

## 3. Cifrado del volumen local

Habilite BitLocker en el volumen que contiene `D:\Inventfarm\Backups`, usando
TPM cuando esté disponible. Guarde la clave de recuperación en el resguardo de
TI, fuera del servidor. No la guarde en el proyecto, en el mismo disco ni en
la copia de base de datos.

## 4. Tarea diaria

Abra PowerShell como administrador en el servidor y ejecute una vez:

```powershell
cd C:\ruta\a\inventfarm
.\scripts\instalar_tarea_respaldo.ps1 `
  -ProjectPath 'C:\ruta\a\inventfarm' `
  -PythonPath 'C:\ruta\a\inventfarm\venv\Scripts\python.exe' `
  -At '02:00'
```

El script solicita la cuenta de servicio y crea la tarea diaria. Antes de dar
por terminada la instalación, ejecútela manualmente desde **Task Scheduler** y
compruebe estos cuatro puntos:

1. Existe un archivo `.sql.gz`, otro `.tar.gz` y otro `.manifest.json` en la
   copia local.
2. Los tres archivos aparecen también en el recurso externo.
3. El panel de copias muestra “Réplica externa disponible”.
4. `logs\respaldo_programado.log` no contiene errores.

## 5. Procesador de operaciones solicitadas desde el panel

Las copias y restauraciones iniciadas desde el panel no se ejecutan dentro de
la ventana del navegador. INVENTFARM las deja en una cola con avance visible,
para que el navegador pueda cerrarse o perder conexión sin interrumpir la
operación. Instale también este procesador, con la misma cuenta de servicio:

```powershell
cd C:\ruta\a\inventfarm
.\scripts\instalar_tarea_cola_respaldos.ps1 `
  -ProjectPath 'C:\ruta\a\inventfarm' `
  -PythonPath 'C:\ruta\a\inventfarm\venv\Scripts\python.exe'
```

La tarea se ejecuta cada minuto y procesa una única solicitud por vez. No
instale varias tareas de procesado ni cambie su política de instancias:
INVENTFARM ya bloquea operaciones simultáneas, pero una sola tarea hace el
diagnóstico y la recuperación más claros.

Compruebe una vez desde **Task Scheduler** que la tarea puede ejecutarse y
que `logs\cola_respaldos.log` no muestra errores. Sin esta tarea, el panel
podrá registrar una solicitud, pero permanecerá correctamente como “En
espera”; no se perderá información ni se iniciará una copia incompleta.

En `.env` se pueden ajustar los límites operativos si la copia real tarda más
de cuatro horas, sin desactivar la protección:

```env
BACKUP_JOB_STALE_MINUTES=240
BACKUP_JOB_STATUS_TOKEN_AGE=3600
```

Durante una restauración activa, el sistema muestra mantenimiento a los
usuarios operativos para impedir movimientos contra una base que está siendo
reemplazada. Las sesiones se invalidan al terminar; el panel conserva un
recibo firmado temporal para comunicar al administrador si la restauración
terminó correctamente.

## 6. Recuperación y prueba mensual

Una vez al mes, TI debe copiar un conjunto externo a un entorno aislado,
configurar la misma `SECRET_KEY` de recuperación y probar la restauración. No
restaure una copia en el servidor productivo para validarla. Registre fecha,
responsable y resultado en la bitácora institucional.

Las copias de INVENTFARM restauran datos y `media`; no reemplazan el respaldo
del sistema operativo, MySQL, certificados, código ni configuración del
servidor. Mantenga además un respaldo de imagen/VM o Windows Server Backup
según la política institucional.
