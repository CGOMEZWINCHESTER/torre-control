BEGIN;

ALTER TABLE torre_residents DROP CONSTRAINT IF EXISTS torre_residents_dept_number_check;
ALTER TABLE torre_residents DROP CONSTRAINT IF EXISTS torre_residents_role_check;

ALTER TABLE torre_residents
ALTER COLUMN dept_number TYPE VARCHAR(1)
USING CASE dept_number::text
    WHEN '101' THEN 'A'
    WHEN '102' THEN 'B'
    WHEN '201' THEN 'C'
    WHEN '202' THEN 'D'
    WHEN '203' THEN 'E'
    WHEN '301' THEN 'F'
    WHEN '302' THEN 'G'
    WHEN '303' THEN 'H'
    WHEN '304' THEN 'I'
    WHEN '305' THEN 'J'
    WHEN 'A' THEN 'A'
    WHEN 'B' THEN 'B'
    WHEN 'C' THEN 'C'
    WHEN 'D' THEN 'D'
    WHEN 'E' THEN 'E'
    WHEN 'F' THEN 'F'
    WHEN 'G' THEN 'G'
    WHEN 'H' THEN 'H'
    WHEN 'I' THEN 'I'
    WHEN 'J' THEN 'J'
    ELSE upper(dept_number::text)
END;

UPDATE torre_residents
SET role = 'admin'
WHERE role = 'committee';

ALTER TABLE torre_residents
ADD CONSTRAINT torre_residents_dept_number_check CHECK (dept_number ~ '^[A-J]$');

ALTER TABLE torre_residents
ADD CONSTRAINT torre_residents_role_check CHECK (role IN ('admin', 'resident'));

UPDATE torre_parking_spots
SET note = replace(replace(replace(replace(replace(note,
    'depto 101', 'depto A'),
    'depto 102', 'depto B'),
    'depto 303', 'depto H'),
    'depto 305', 'depto J'),
    'depto 302', 'depto G'),
    location = replace(location, 'calle Roble', 'calle 40');

UPDATE torre_announcements
SET title = replace(title, 'Torre Roble', 'Torre 40'),
    body = replace(body, 'Torre Roble', 'Torre 40'),
    updated_at = now()
WHERE title LIKE '%Torre Roble%' OR body LIKE '%Torre Roble%';

COMMIT;
