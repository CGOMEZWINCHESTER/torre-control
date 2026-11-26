BEGIN;

CREATE TABLE IF NOT EXISTS torre_residents (
    id BIGSERIAL PRIMARY KEY,
    dept_number VARCHAR(1) NOT NULL UNIQUE CHECK (dept_number ~ '^[A-J]$'),
    name VARCHAR(60) NOT NULL CHECK (char_length(name) BETWEEN 1 AND 60),
    role VARCHAR(16) NOT NULL DEFAULT 'resident' CHECK (role IN ('admin', 'resident')),
    phone VARCHAR(32) CHECK (char_length(phone) BETWEEN 7 AND 32),
    emergency_name VARCHAR(60) CHECK (char_length(emergency_name) BETWEEN 1 AND 60),
    emergency_phone VARCHAR(32) CHECK (char_length(emergency_phone) BETWEEN 7 AND 32),
    avatar_color VARCHAR(7) NOT NULL DEFAULT '#6366f1' CHECK (avatar_color ~ '^#[0-9A-Fa-f]{6}$'),
    avatar_icon VARCHAR(8) NOT NULL DEFAULT 'TC' CHECK (char_length(avatar_icon) BETWEEN 1 AND 8),
    pin_hash TEXT NOT NULL CHECK (char_length(pin_hash) BETWEEN 1 AND 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS torre_announcements (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(140) NOT NULL CHECK (char_length(title) BETWEEN 1 AND 140),
    body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 4000),
    category VARCHAR(24) NOT NULL DEFAULT 'Avisos Generales' CHECK (category IN ('Urgente', 'Mantenimiento', 'Avisos Generales', 'Acuerdos')),
    is_pinned BOOLEAN NOT NULL DEFAULT false,
    created_by BIGINT NOT NULL REFERENCES torre_residents(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS torre_announcement_reads (
    id BIGSERIAL PRIMARY KEY,
    announcement_id BIGINT NOT NULL REFERENCES torre_announcements(id) ON DELETE CASCADE,
    resident_id BIGINT NOT NULL REFERENCES torre_residents(id) ON DELETE CASCADE,
    read_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_torre_announcement_reads_announcement_resident UNIQUE (announcement_id, resident_id)
);

CREATE TABLE IF NOT EXISTS torre_announcement_comments (
    id BIGSERIAL PRIMARY KEY,
    announcement_id BIGINT NOT NULL REFERENCES torre_announcements(id) ON DELETE CASCADE,
    resident_id BIGINT NOT NULL REFERENCES torre_residents(id) ON DELETE RESTRICT,
    body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS torre_chores (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(140) NOT NULL CHECK (char_length(title) BETWEEN 1 AND 140),
    description TEXT CHECK (char_length(description) <= 2000),
    area VARCHAR(24) NOT NULL DEFAULT 'Otro' CHECK (area IN ('Escaleras', 'Pasillos', 'Área de basura', 'Tinacos', 'Cisterna', 'Jardín', 'Otro')),
    frequency VARCHAR(16) NOT NULL DEFAULT 'Única' CHECK (frequency IN ('Semanal', 'Mensual', 'Única')),
    due_date DATE,
    assigned_to BIGINT REFERENCES torre_residents(id) ON DELETE SET NULL,
    created_by BIGINT NOT NULL REFERENCES torre_residents(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_completed BOOLEAN NOT NULL DEFAULT false,
    completed_at TIMESTAMPTZ,
    completed_by BIGINT REFERENCES torre_residents(id) ON DELETE SET NULL,
    evidence_url TEXT CHECK (evidence_url IS NULL OR (char_length(evidence_url) <= 1500000 AND evidence_url ~ '^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$')),
    next_chore_id BIGINT REFERENCES torre_chores(id) ON DELETE SET NULL,
    CONSTRAINT ck_torre_chores_completed_fields CHECK (is_completed = (completed_at IS NOT NULL AND completed_by IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS torre_expenses (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(140) NOT NULL CHECK (char_length(title) BETWEEN 1 AND 140),
    category VARCHAR(24) NOT NULL DEFAULT 'Otro' CHECK (category IN ('Limpieza', 'Reparación', 'Luz', 'Agua', 'Seguridad', 'Otro')),
    amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    spent_on DATE NOT NULL,
    receipt_url TEXT CHECK (receipt_url IS NULL OR (char_length(receipt_url) <= 1500000 AND receipt_url ~ '^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$')),
    created_by BIGINT NOT NULL REFERENCES torre_residents(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS torre_contributions (
    id BIGSERIAL PRIMARY KEY,
    resident_id BIGINT NOT NULL REFERENCES torre_residents(id) ON DELETE RESTRICT,
    kind VARCHAR(32) NOT NULL CHECK (kind IN ('Cuota mensual', 'Cooperación extraordinaria')),
    period VARCHAR(7) NOT NULL CHECK (period ~ '^[0-9]{4}-[0-9]{2}$'),
    amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    proof_url TEXT CHECK (proof_url IS NULL OR (char_length(proof_url) <= 1500000 AND proof_url ~ '^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$')),
    status VARCHAR(16) NOT NULL DEFAULT 'Pendiente' CHECK (status IN ('Pendiente', 'Aprobada', 'Rechazada')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    approved_by BIGINT REFERENCES torre_residents(id) ON DELETE RESTRICT,
    CONSTRAINT ck_torre_contributions_approval CHECK ((status = 'Aprobada' AND approved_at IS NOT NULL AND approved_by IS NOT NULL) OR (status <> 'Aprobada' AND approved_at IS NULL AND approved_by IS NULL))
);

CREATE TABLE IF NOT EXISTS torre_parking_spots (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(24) NOT NULL UNIQUE CHECK (char_length(code) BETWEEN 1 AND 24),
    location VARCHAR(120) NOT NULL CHECK (char_length(location) BETWEEN 1 AND 120),
    spot_type VARCHAR(16) NOT NULL DEFAULT 'Cubo' CHECK (spot_type IN ('Cubo', 'Descubierto')),
    status VARCHAR(16) NOT NULL DEFAULT 'Disponible' CHECK (status IN ('Disponible', 'Solicitado', 'Prestado')),
    owner_id BIGINT REFERENCES torre_residents(id) ON DELETE RESTRICT,
    borrower_id BIGINT REFERENCES torre_residents(id) ON DELETE SET NULL,
    loan_until DATE,
    note TEXT,
    CONSTRAINT ck_parking_available CHECK (status <> 'Disponible' OR borrower_id IS NULL),
    CONSTRAINT ck_parking_loaned CHECK (status <> 'Prestado' OR borrower_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_torre_residents_dept_number ON torre_residents (dept_number);
CREATE INDEX IF NOT EXISTS ix_torre_residents_role ON torre_residents (role);
CREATE INDEX IF NOT EXISTS ix_torre_announcements_pinned ON torre_announcements (is_pinned DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_torre_announcements_created_at ON torre_announcements (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_torre_announcements_category ON torre_announcements (category);
CREATE INDEX IF NOT EXISTS ix_torre_announcements_creator ON torre_announcements (created_by);
CREATE INDEX IF NOT EXISTS ix_torre_announcement_reads_resident ON torre_announcement_reads (resident_id);
CREATE INDEX IF NOT EXISTS ix_torre_announcement_reads_read_at ON torre_announcement_reads (read_at DESC);
CREATE INDEX IF NOT EXISTS ix_torre_announcement_comments_announcement ON torre_announcement_comments (announcement_id, created_at);
CREATE INDEX IF NOT EXISTS ix_torre_announcement_comments_resident ON torre_announcement_comments (resident_id);
CREATE INDEX IF NOT EXISTS ix_torre_chores_completed ON torre_chores (is_completed);
CREATE INDEX IF NOT EXISTS ix_torre_chores_due_date ON torre_chores (due_date);
CREATE INDEX IF NOT EXISTS ix_torre_chores_assigned_to ON torre_chores (assigned_to);
CREATE INDEX IF NOT EXISTS ix_torre_chores_created_at ON torre_chores (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_torre_chores_completed_at ON torre_chores (completed_at DESC);
CREATE INDEX IF NOT EXISTS ix_torre_expenses_spent_on ON torre_expenses (spent_on DESC);
CREATE INDEX IF NOT EXISTS ix_torre_expenses_creator ON torre_expenses (created_by);
CREATE INDEX IF NOT EXISTS ix_torre_expenses_created_at ON torre_expenses (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_torre_contributions_resident ON torre_contributions (resident_id);
CREATE INDEX IF NOT EXISTS ix_torre_contributions_period ON torre_contributions (period);
CREATE INDEX IF NOT EXISTS ix_torre_contributions_status ON torre_contributions (status);
CREATE INDEX IF NOT EXISTS ix_torre_contributions_approved_by ON torre_contributions (approved_by);
CREATE INDEX IF NOT EXISTS ix_torre_parking_spots_status ON torre_parking_spots (status);
CREATE INDEX IF NOT EXISTS ix_torre_parking_spots_owner ON torre_parking_spots (owner_id);
CREATE INDEX IF NOT EXISTS ix_torre_parking_spots_borrower ON torre_parking_spots (borrower_id);

INSERT INTO torre_residents (id, dept_number, name, role, phone, emergency_name, emergency_phone, avatar_color, avatar_icon, pin_hash, created_at)
VALUES
    (1, 'A', 'Laura Martínez', 'resident', '55 1234 5678', 'Roberto Martínez', '55 8765 4321', '#b45309', 'LM', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:00:00-06'),
    (2, 'B', 'Diego Ramírez', 'admin', '55 2345 6789', 'Mónica Ramírez', '55 9876 5432', '#2563eb', 'DR', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:05:00-06'),
    (3, 'C', 'Fernanda López', 'resident', '55 3456 7890', 'Javier López', '55 1111 2222', '#db2777', 'FL', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:10:00-06'),
    (4, 'D', 'Álvaro Hernández', 'resident', '55 4567 8901', 'Lucía Hernández', '55 2222 3333', '#059669', 'AH', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:15:00-06'),
    (5, 'E', 'Mariana González', 'resident', '55 5678 9012', 'Carlos González', '55 3333 4444', '#7c3aed', 'MG', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:20:00-06'),
    (6, 'F', 'Javier Torres', 'resident', '55 6789 0123', 'Elena Torres', '55 4444 5555', '#dc2626', 'JT', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:25:00-06'),
    (7, 'G', 'Carolina Vázquez', 'resident', '55 7890 1234', 'Andrés Vázquez', '55 5555 6666', '#0891b2', 'CV', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:30:00-06'),
    (8, 'H', 'Ricardo Solís', 'resident', '55 8901 2345', 'Patricia Solís', '55 6666 7777', '#ea580c', 'RS', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:35:00-06'),
    (9, 'I', 'Paola Medina', 'resident', '55 9012 3456', 'Hugo Medina', '55 7777 8888', '#4f46e5', 'PM', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:40:00-06'),
    (10, 'J', 'Enrique Flores', 'resident', '55 0123 4567', 'Sofía Flores', '55 8888 9999', '#65a30d', 'EF', '$2b$10$qyS41qZ0ZnlLXuzo0DlFZOQHmKDIFD8D6p3boCFLVu87PZ4QElI9K', TIMESTAMPTZ '2026-11-01 09:45:00-06')
ON CONFLICT (id) DO NOTHING;

INSERT INTO torre_announcements (id, title, body, category, is_pinned, created_by, created_at, updated_at)
VALUES
    (1, 'Falla en la bomba de agua', 'La bomba del tinaco principal presentó una falla esta mañana. Ya acudimos el técnico y estimamos restablecer el servicio antes de las 18:00. Eviten usar el agua de las llaves comunes mientras termina la reparación.', 'Urgente', true, 1, TIMESTAMPTZ '2026-11-25 08:15:00-06', TIMESTAMPTZ '2026-11-25 09:40:00-06'),
    (2, 'Corte de agua programado', 'El jueves 26 de noviembre de 09:00 a 13:00 se suspenderá el suministro por trabajos en la cisterna. Por favor llenen sus recipientes con anticipación y mantengan cerradas las llaves.', 'Urgente', false, 1, TIMESTAMPTZ '2026-11-24 18:00:00-06', TIMESTAMPTZ '2026-11-24 18:00:00-06'),
    (3, 'Mantenimiento de elevadores', 'El viernes 27 de noviembre, de 10:00 a 14:00, se realizará la revisión mensual de los elevadores. Habrá un técnico en el vestíbulo para atender cualquier duda.', 'Mantenimiento', false, 1, TIMESTAMPTZ '2026-11-23 11:30:00-06', TIMESTAMPTZ '2026-11-23 11:30:00-06'),
    (4, 'Limpieza de tinacos', 'El sábado 28 se limpiarán los tinacos de los niveles 2 y 3. El acceso a las azoteas estará restringido durante la mañana; avisen si dejaron objetos personales en esas áreas.', 'Mantenimiento', false, 1, TIMESTAMPTZ '2026-11-22 16:10:00-06', TIMESTAMPTZ '2026-11-22 16:10:00-06'),
    (5, 'Acuerdo de asamblea: horario de basura', 'Por unanimidad se acordó depositar la basura en el área designada de 19:00 a 21:00, de lunes a domingo. Se colocará un letrero junto a los contenedores para recordar el horario.', 'Acuerdos', false, 1, TIMESTAMPTZ '2026-11-20 12:00:00-06', TIMESTAMPTZ '2026-11-20 12:00:00-06'),
    (6, 'Reunión de vecinos de Torre 40', 'Convocamos a todos los departamentos a la reunión del domingo 29 de noviembre a las 10:00 en el salón comunal. Trataremos el presupuesto de diciembre y el uso de los estacionamientos.', 'Avisos Generales', false, 1, TIMESTAMPTZ '2026-11-18 17:45:00-06', TIMESTAMPTZ '2026-11-18 17:45:00-06')
ON CONFLICT (id) DO NOTHING;

INSERT INTO torre_announcement_reads (id, announcement_id, resident_id, read_at)
VALUES
    (1, 1, 2, TIMESTAMPTZ '2026-11-25 08:30:00-06'),
    (2, 1, 3, TIMESTAMPTZ '2026-11-25 08:33:00-06'),
    (3, 1, 4, TIMESTAMPTZ '2026-11-25 08:41:00-06'),
    (4, 1, 5, TIMESTAMPTZ '2026-11-25 08:47:00-06'),
    (5, 1, 6, TIMESTAMPTZ '2026-11-25 09:02:00-06'),
    (6, 1, 7, TIMESTAMPTZ '2026-11-25 09:08:00-06'),
    (7, 1, 8, TIMESTAMPTZ '2026-11-25 09:15:00-06'),
    (8, 2, 2, TIMESTAMPTZ '2026-11-24 18:20:00-06'),
    (9, 2, 3, TIMESTAMPTZ '2026-11-24 18:26:00-06'),
    (10, 2, 4, TIMESTAMPTZ '2026-11-24 18:32:00-06'),
    (11, 2, 9, TIMESTAMPTZ '2026-11-24 19:05:00-06'),
    (12, 2, 10, TIMESTAMPTZ '2026-11-24 19:14:00-06'),
    (13, 3, 3, TIMESTAMPTZ '2026-11-23 12:10:00-06'),
    (14, 3, 5, TIMESTAMPTZ '2026-11-23 12:22:00-06'),
    (15, 3, 6, TIMESTAMPTZ '2026-11-23 13:40:00-06'),
    (16, 4, 4, TIMESTAMPTZ '2026-11-22 17:00:00-06'),
    (17, 4, 7, TIMESTAMPTZ '2026-11-22 17:12:00-06'),
    (18, 4, 8, TIMESTAMPTZ '2026-11-22 18:03:00-06'),
    (19, 5, 2, TIMESTAMPTZ '2026-11-20 13:15:00-06'),
    (20, 5, 4, TIMESTAMPTZ '2026-11-20 13:29:00-06'),
    (21, 5, 9, TIMESTAMPTZ '2026-11-20 14:02:00-06'),
    (22, 6, 1, TIMESTAMPTZ '2026-11-18 18:00:00-06'),
    (23, 6, 3, TIMESTAMPTZ '2026-11-18 18:21:00-06'),
    (24, 6, 10, TIMESTAMPTZ '2026-11-18 19:10:00-06')
ON CONFLICT (id) DO NOTHING;

INSERT INTO torre_announcement_comments (id, announcement_id, resident_id, body, created_at)
VALUES
    (1, 1, 2, 'Gracias por avisar tan rápido. ¿Ya llamaron al plomero de guardia?', TIMESTAMPTZ '2026-11-25 09:05:00-06'),
    (2, 1, 5, 'En el cuarto piso todavía sale poca presión, pero ya no hay ruido en la tubería.', TIMESTAMPTZ '2026-11-25 09:12:00-06'),
    (3, 2, 8, '¿El corte también afectará el agua caliente de los baños?', TIMESTAMPTZ '2026-11-24 19:30:00-06'),
    (4, 5, 3, 'Perfecto, pongo el aviso en el elevador para que nadie lo olvide.', TIMESTAMPTZ '2026-11-21 10:00:00-06')
ON CONFLICT (id) DO NOTHING;

INSERT INTO torre_chores (id, title, description, area, frequency, due_date, assigned_to, created_by, created_at, is_completed, completed_at, completed_by, evidence_url, next_chore_id)
VALUES
    (1, 'Limpieza de escaleras, entreplanta', 'Barrer y trapear los escalones entre el primer y segundo piso.', 'Escaleras', 'Semanal', DATE '2026-11-23', 3, 1, TIMESTAMPTZ '2026-11-16 10:00:00-06', false, NULL, NULL, NULL, NULL),
    (2, 'Barrido de pasillos del tercer piso', 'Barrer el pasillo completo y revisar los rodapiés.', 'Pasillos', 'Semanal', DATE '2026-11-24', 8, 1, TIMESTAMPTZ '2026-11-17 10:00:00-06', false, NULL, NULL, NULL, NULL),
    (3, 'Extracción de basura de los contenedores', 'Sacar los contenedores a la banqueta y lavar la tapa.', 'Área de basura', 'Semanal', DATE '2026-11-26', 4, 1, TIMESTAMPTZ '2026-11-19 10:00:00-06', false, NULL, NULL, NULL, NULL),
    (4, 'Revisión de tinacos', 'Revisar nivel de agua, flotador y fugas en las conexiones.', 'Tinacos', 'Mensual', DATE '2026-11-27', 6, 1, TIMESTAMPTZ '2026-11-01 10:00:00-06', false, NULL, NULL, NULL, NULL),
    (5, 'Limpieza de cisterna', 'Vaciar, cepillar paredes y desinfectar la cisterna principal.', 'Cisterna', 'Mensual', DATE '2026-11-21', 6, 1, TIMESTAMPTZ '2026-11-02 10:00:00-06', true, TIMESTAMPTZ '2026-11-21 17:30:00-06', 6, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', NULL),
    (6, 'Riego y poda del jardín', 'Regar las plantas de la entrada y podar los arbustos bajos.', 'Jardín', 'Semanal', DATE '2026-11-22', 9, 1, TIMESTAMPTZ '2026-11-15 10:00:00-06', true, TIMESTAMPTZ '2026-11-22 10:15:00-06', 9, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', NULL),
    (7, 'Desinfección de pasamanos', 'Limpiar pasamanos de todas las escaleras con cloro diluido.', 'Escaleras', 'Única', DATE '2026-11-19', 2, 1, TIMESTAMPTZ '2026-11-14 10:00:00-06', true, TIMESTAMPTZ '2026-11-20 12:00:00-06', 2, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', NULL),
    (8, 'Revisión de lámparas de pasillo', 'Cambiar dos focos quemados del segundo piso.', 'Pasillos', 'Mensual', DATE '2026-11-18', 7, 1, TIMESTAMPTZ '2026-11-03 10:00:00-06', true, TIMESTAMPTZ '2026-11-19 16:00:00-06', 7, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', NULL),
    (9, 'Retiro de escombros en cochera', 'Retirar los sacos de material que quedaron junto a la rampa.', 'Otro', 'Única', DATE '2026-11-25', 10, 1, TIMESTAMPTZ '2026-11-21 10:00:00-06', false, NULL, NULL, NULL, NULL),
    (10, 'Revisión de cerradura del portón', 'Ajustar la cerradura y probar el control de acceso.', 'Otro', 'Única', DATE '2026-11-30', 1, 1, TIMESTAMPTZ '2026-11-24 10:00:00-06', false, NULL, NULL, NULL, NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO torre_expenses (id, title, category, amount, spent_on, receipt_url, created_by, created_at)
VALUES
    (1, 'Servicio de limpieza de escaleras', 'Limpieza', 2400.00, DATE '2026-11-03', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 1, TIMESTAMPTZ '2026-11-03 18:00:00-06'),
    (2, 'Reparación de bomba de agua', 'Reparación', 3850.00, DATE '2026-11-05', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 1, TIMESTAMPTZ '2026-11-05 17:20:00-06'),
    (3, 'Consumo de luz de áreas comunes', 'Luz', 1875.50, DATE '2026-11-10', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 1, TIMESTAMPTZ '2026-11-10 12:00:00-06'),
    (4, 'Consumo de agua del edificio', 'Agua', 1240.00, DATE '2026-11-10', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 1, TIMESTAMPTZ '2026-11-10 12:05:00-06'),
    (5, 'Mantenimiento de cámaras de seguridad', 'Seguridad', 2100.00, DATE '2026-11-14', NULL, 1, TIMESTAMPTZ '2026-11-14 16:00:00-06'),
    (6, 'Materiales para jardinería', 'Otro', 860.00, DATE '2026-11-18', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 1, TIMESTAMPTZ '2026-11-18 13:30:00-06'),
    (7, 'Compra de focos LED para pasillos', 'Reparación', 695.00, DATE '2026-11-22', NULL, 1, TIMESTAMPTZ '2026-11-22 11:15:00-06')
ON CONFLICT (id) DO NOTHING;

INSERT INTO torre_contributions (id, resident_id, kind, period, amount, proof_url, status, created_at, approved_at, approved_by)
VALUES
    (1, 1, 'Cuota mensual', '2026-11', 850.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Aprobada', TIMESTAMPTZ '2026-11-02 10:00:00-06', TIMESTAMPTZ '2026-11-02 12:00:00-06', 1),
    (2, 2, 'Cuota mensual', '2026-11', 850.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Aprobada', TIMESTAMPTZ '2026-11-03 09:30:00-06', TIMESTAMPTZ '2026-11-03 11:00:00-06', 1),
    (3, 3, 'Cuota mensual', '2026-11', 850.00, NULL, 'Aprobada', TIMESTAMPTZ '2026-11-04 16:45:00-06', TIMESTAMPTZ '2026-11-04 18:00:00-06', 1),
    (4, 4, 'Cuota mensual', '2026-11', 850.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Aprobada', TIMESTAMPTZ '2026-11-05 10:10:00-06', TIMESTAMPTZ '2026-11-05 12:15:00-06', 1),
    (5, 5, 'Cuota mensual', '2026-11', 850.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Aprobada', TIMESTAMPTZ '2026-11-06 11:20:00-06', TIMESTAMPTZ '2026-11-06 13:00:00-06', 1),
    (6, 6, 'Cuota mensual', '2026-11', 850.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Aprobada', TIMESTAMPTZ '2026-11-07 09:00:00-06', TIMESTAMPTZ '2026-11-07 10:30:00-06', 1),
    (7, 9, 'Cuota mensual', '2026-11', 850.00, NULL, 'Aprobada', TIMESTAMPTZ '2026-11-08 17:40:00-06', TIMESTAMPTZ '2026-11-08 19:00:00-06', 1),
    (8, 7, 'Cuota mensual', '2026-11', 850.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Pendiente', TIMESTAMPTZ '2026-11-23 20:15:00-06', NULL, NULL),
    (9, 7, 'Cuota mensual', '2026-11', 850.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Rechazada', TIMESTAMPTZ '2026-11-10 18:05:00-06', NULL, NULL),
    (10, 8, 'Cooperación extraordinaria', '2026-11', 500.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Aprobada', TIMESTAMPTZ '2026-11-12 12:00:00-06', TIMESTAMPTZ '2026-11-12 13:30:00-06', 1),
    (11, 10, 'Cooperación extraordinaria', '2026-11', 1000.00, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/n6kAAAAASUVORK5CYII=', 'Aprobada', TIMESTAMPTZ '2026-11-15 10:40:00-06', TIMESTAMPTZ '2026-11-15 11:50:00-06', 1)
ON CONFLICT (id) DO NOTHING;

INSERT INTO torre_parking_spots (id, code, location, spot_type, status, owner_id, borrower_id, loan_until, note)
VALUES
    (1, 'P-01', 'Subterráneo nivel -1, zona A', 'Cubo', 'Disponible', 1, NULL, NULL, 'Lugar asignado al depto A'),
    (2, 'P-02', 'Subterráneo nivel -1, zona A', 'Cubo', 'Disponible', 2, NULL, NULL, 'Uso exclusivo del depto B'),
    (3, 'P-03', 'Subterráneo nivel -1, zona B', 'Descubierto', 'Prestado', 3, 8, DATE '2026-12-05', 'Préstamo temporal al depto H'),
    (4, 'P-04', 'Subterráneo nivel -1, zona B', 'Cubo', 'Disponible', 4, NULL, NULL, 'Cubo con llave en caseta'),
    (5, 'P-05', 'Planta baja, frente a entrada', 'Descubierto', 'Prestado', 5, 10, DATE '2026-12-01', 'Dejado al depto J durante la obra'),
    (6, 'P-06', 'Planta baja, frente a entrada', 'Cubo', 'Solicitado', 6, 7, NULL, 'Solicitud pendiente del depto G'),
    (7, 'P-07', 'Lateral calle 40, frente al jardín', 'Descubierto', 'Disponible', 7, NULL, NULL, 'Sin restricción de horario'),
    (8, 'P-08', 'Subterráneo nivel -2, zona C', 'Cubo', 'Disponible', 9, NULL, NULL, 'Cerca del cuarto de máquinas')
ON CONFLICT (id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('torre_residents', 'id'), COALESCE((SELECT MAX(id) FROM torre_residents), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('torre_announcements', 'id'), COALESCE((SELECT MAX(id) FROM torre_announcements), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('torre_announcement_reads', 'id'), COALESCE((SELECT MAX(id) FROM torre_announcement_reads), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('torre_announcement_comments', 'id'), COALESCE((SELECT MAX(id) FROM torre_announcement_comments), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('torre_chores', 'id'), COALESCE((SELECT MAX(id) FROM torre_chores), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('torre_expenses', 'id'), COALESCE((SELECT MAX(id) FROM torre_expenses), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('torre_contributions', 'id'), COALESCE((SELECT MAX(id) FROM torre_contributions), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('torre_parking_spots', 'id'), COALESCE((SELECT MAX(id) FROM torre_parking_spots), 0) + 1, false);

COMMIT;
