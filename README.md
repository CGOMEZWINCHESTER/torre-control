# Torre Control

PWA para la administración de "Torre Roble": tablón de anuncios, tareas de limpieza y mantenimiento, finanzas (egresos y aportaciones) y gestión de estacionamientos. Cada departamento entra con su número y un PIN de demostración.

## Stack

- Python 3.12 (`.python-version`).
- FastAPI + Uvicorn, SQLAlchemy 2, PostgreSQL/Supabase con `psycopg[binary]`.
- Pydantic 2 y `pydantic-settings` para contratos y configuración.
- `itsdangerous` para cookies de sesión firmadas y `bcrypt` para los PIN.
- `httpx` para pruebas/cliente HTTP.
- Frontend estático en `static/` (HTML, CSS, JS, manifest y service worker), servido por la propia FastAPI.

## Estructura

```text
torre-control/
├── app/
│   ├── config.py            # configuración desde variables de entorno
│   ├── database.py          # engine y sesiones SQLAlchemy
│   ├── deps.py              # autenticación y permisos
│   ├── main.py              # app FastAPI + routers + static
│   ├── models.py            # modelos ORM
│   ├── routers/             # auth, residents, board, chores, finance, parking
│   ├── schemas.py           # contratos Pydantic
│   └── services/            # seguridad, imágenes, recurrencia, residentes
├── db/
│   ├── schema.sql           # DDL idempotente + seed de demostración
│   └── migrations/
│       └── 001_initial.sql  # copia idéntica de schema.sql
├── static/                  # PWA (no modificada en esta entrega)
├── main.py                  # entrypoint para Vercel: from app.main import app
├── requirements.txt
├── .env.example
├── vercel-env.example.txt
└── vercel.json
```

## Base de datos

`db/schema.sql` crea ocho tablas con `CREATE TABLE IF NOT EXISTS`, `CHECK`s, índices y datos de prueba en español (México):

| Tabla | Contenido del seed |
| --- | --- |
| `residents` | 10 departamentos, 1 `committee` y 9 `resident` |
| `announcements` | 6 anuncios: 2 urgentes (uno fijado), 2 mantenimiento, 1 acuerdo y 1 aviso general |
| `announcement_reads` | 24 lecturas repartidas entre anuncios y residentes |
| `announcement_comments` | 4 comentarios realistas |
| `chores` | 10 tareas: 2 atrasadas, 2 próximas a vencer y 4 completadas con evidencia |
| `expenses` | 7 egresos de noviembre 2026, 5 con comprobante |
| `contributions` | 8 cuotas (7 aprobadas, 1 pendiente, 1 rechazada) y 2 cooperaciones aprobadas |
| `parking_spots` | 8 lugares `P-01` a `P-08` con dueños distintos |

Detalles del seed:

- El PIN de todos los residentes es `1234` y usa el mismo hash bcrypt: `$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K`.
- Evidencias, comprobantes y recibos usan la misma data URL PNG válida de 1 píxel.
- La lista del enunciado traía 9 números de departamento; se añadió el `305` para completar los 10.
- Se añadió la columna `chores.next_chore_id` porque el backend la usa al generar la siguiente tarea recurrente; no estaba en la lista resumida del contrato.
- Con los datos de noviembre 2026, los deptos `302` (sin cuota aprobada) y `303` (cooperación de $500.00) quedan "Con adeudo"; el depto `305` se pone al corriente con una cooperación de $1,000.00.

## Puesta en marcha local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
createdb torre_control
psql "postgresql://postgres:postgres@localhost:5432/torre_control" -v ON_ERROR_STOP=1 -f db/schema.sql
uvicorn main:app --reload
```

Abre `http://localhost:8000` para la PWA, `http://localhost:8000/docs` para Swagger y `GET /api/health` para el estado.

Para reiniciar el demo, recrea la base de datos y vuelve a aplicar `db/schema.sql`. El script es idempotente y también puede ejecutarse dos veces seguidas.

## Supabase y Vercel

1. Crea un proyecto Supabase y copia la cadena de conexión del pooler (transaction, puerto `6543`) con `?sslmode=require`.
2. Pégala en `DATABASE_URL` (usa `vercel-env.example.txt` como referencia). El driver debe ser `postgresql+psycopg://...`.
3. Ejecuta todo `db/schema.sql` en el SQL Editor de Supabase (o `db/migrations/001_initial.sql`, que es idéntico).
4. Genera el secreto de sesión con `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` y ponlo en `SESSION_SECRET`.
5. En Vercel usa esas mismas variables, `SECURE_COOKIES=true` y `DB_POOL_CLASS=null` (pool desactivado en serverless).
6. `vercel.json` despliega `main.py` con `maxDuration: 10`.

No se usa Supabase Storage: las imágenes viajan como data URL y se validan en `app/services/images.py`.

## Login de prueba

Selecciona el departamento en la pantalla de ingreso y escribe el PIN `1234`.

| Departamento | Residente | Rol | Situación en 2026-11 |
| --- | --- | --- | --- |
| 101 | Laura Martínez | `committee` | Al corriente |
| 102 | Diego Ramírez | `resident` | Al corriente |
| 201 | Fernanda López | `resident` | Al corriente |
| 202 | Álvaro Hernández | `resident` | Al corriente |
| 203 | Mariana González | `resident` | Al corriente |
| 301 | Javier Torres | `resident` | Al corriente |
| 302 | Carolina Vázquez | `resident` | Con adeudo |
| 303 | Ricardo Solís | `resident` | Con adeudo |
| 304 | Paola Medina | `resident` | Al corriente |
| 305 | Enrique Flores | `resident` | Al corriente |

El estado se calcula en `app/services/residents.py` sumando aportaciones aprobadas del **mes actual**; si se ejecuta fuera de noviembre 2026, actualiza los valores de `period` en el seed o cambia la fecha del sistema para ver los estados anteriores.

## Roles

`committee` (depto 101):

- Publicar, editar, fijar y eliminar anuncios.
- Crear, editar y eliminar tareas; cerrarlas o reabrirlas.
- Aprobar o rechazar aportaciones.
- Registrar, editar y eliminar egresos.
- Administrar lugares de estacionamiento y datos de contacto de residentes.

`resident`:

- Marcar como completadas o reabrir las tareas asignadas y adjuntar evidencia.
- Subir comprobantes de aportaciones y publicar/eliminar sus comentarios.
- Publicar anuncios en la pizarra; solo el comité puede fijarlos arriba.
- Marcar anuncios como leídos.
- Solicitar un estacionamiento; la aprobación o liberación corresponde al comité o al dueño del lugar.

## Endpoints principales

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/api/health` | Estado del servicio |
| `GET` | `/api/auth/profiles` | Perfiles para la pantalla de ingreso |
| `POST` | `/api/auth/login` | Ingreso con `dept_number` y `pin` |
| `POST` | `/api/auth/logout` | Cierra la sesión |
| `GET` | `/api/auth/me` | Residente autenticado y su estado de pago |
| `GET` | `/api/residents` | Lista de residentes |
| `PATCH` | `/api/residents/{id}` | Edita contacto/rol (comité) |
| `GET` / `POST` | `/api/announcements` | Lista y crea anuncios |
| `PATCH` / `DELETE` | `/api/announcements/{id}` | Edita y elimina anuncios |
| `POST` / `DELETE` | `/api/announcements/{id}/read` | Marca o desmarca lectura |
| `POST` | `/api/announcements/{id}/comments` | Publica un comentario |
| `DELETE` | `/api/announcements/{id}/comments/{comment_id}` | Elimina un comentario |
| `GET` | `/api/chores?filter=all\|mine\|pending\|completed` | Lista tareas con filtro |
| `POST` | `/api/chores` | Crea una tarea (comité) |
| `PATCH` / `DELETE` | `/api/chores/{id}` | Edita y elimina una tarea |
| `POST` | `/api/chores/{id}/complete` | Completa con evidencia y genera recurrencia |
| `POST` | `/api/chores/{id}/reopen` | Reabre una tarea |
| `GET` / `POST` | `/api/expenses` | Lista y registra egresos |
| `PATCH` / `DELETE` | `/api/expenses/{id}` | Edita y elimina egresos |
| `GET` / `POST` | `/api/contributions` | Lista y registra aportaciones |
| `POST` | `/api/contributions/{id}/review` | Aprobación (`approve`) o rechazo (`reject`) |
| `GET` | `/api/finance/summary` | Resumen de caja del mes |
| `GET` / `POST` | `/api/parking` | Lista y crea lugares |
| `PATCH` / `DELETE` | `/api/parking/{id}` | Edita y elimina lugares |
| `POST` | `/api/parking/{id}/request` | Solicita un lugar |
| `POST` | `/api/parking/{id}/approve` | Aprueba el préstamo |
| `POST` | `/api/parking/{id}/release` | Libera el lugar |

## Notas PWA

- FastAPI monta `static/` en `/`; el service worker y el manifest están en esa carpeta.
- El service worker usa caché para el shell y para respuestas `GET /api/...`, separando por cabecera `X-User-Id`. Al cambiar de perfil conviene limpiar la caché de la API.
- El registro del service worker requiere HTTPS o `localhost`; en producción `SECURE_COOKIES=true`.
- El manifest se llama "Torre Roble · Control vecinal" y el service worker usa las cachés `torre-shell-v2` y `torre-api-v2`.

## Comandos de validación

```bash
pip check
python3 -m compileall -q app main.py
python3 -c 'import bcrypt; print(bcrypt.checkpw(b"1234", b"$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K"))'
python3 -c "import pathlib; s=pathlib.Path('db/schema.sql').read_text(encoding='utf-8'); print(s.count('CREATE TABLE IF NOT EXISTS'), s.count('setval(pg_get_serial_sequence'))"
python3 -c "import pathlib; print([i for i, l in enumerate(pathlib.Path('db/schema.sql').read_text(encoding='utf-8').splitlines(), 1) if l.count(chr(39)) % 2])"
psql "postgresql://postgres:postgres@localhost:5432/torre_control" -v ON_ERROR_STOP=1 -f db/schema.sql
```

Esperado: `True`, `8 8` y `[]` (ninguna línea con comillas simples sin cerrar). No hay suite de pruebas en el repositorio; la verificación adicional es `GET /api/health` y el uso de `/docs`.
