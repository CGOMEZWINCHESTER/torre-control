BEGIN;

ALTER TABLE torre_residents DROP CONSTRAINT IF EXISTS torre_residents_dept_number_check;
ALTER TABLE torre_residents DROP CONSTRAINT IF EXISTS torre_residents_role_check;

DO $$
BEGIN
    IF EXISTS (
        WITH letters(letter, code) AS (
            VALUES ('A', 101), ('B', 102), ('C', 201), ('D', 202), ('E', 203),
                   ('F', 301), ('G', 302), ('H', 303), ('I', 304), ('J', 305)
        ),
        ranked AS (
            SELECT r.id,
                   l.letter AS known_letter,
                   l.code AS known_code,
                   sum(CASE WHEN l.letter IS NULL THEN 1 ELSE 0 END) OVER (
                       ORDER BY r.id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                   ) AS unknown_rn
            FROM torre_residents r
            LEFT JOIN letters l
              ON l.code::text = r.dept_number::text
              OR l.letter = upper(r.dept_number::text)
        ),
        free AS (
            SELECT l.letter,
                   l.code,
                   row_number() OVER (ORDER BY l.letter) AS rn
            FROM letters l
            WHERE NOT EXISTS (
                SELECT 1 FROM ranked r WHERE r.known_code = l.code
            )
        ),
        assigned AS (
            SELECT r.id,
                   COALESCE(
                       r.known_code,
                       (SELECT f.code FROM free f WHERE f.rn = r.unknown_rn)
                   ) AS new_code
            FROM ranked r
        )
        SELECT 1 FROM assigned WHERE new_code IS NULL
    ) THEN
        RAISE EXCEPTION 'No hay letras A-J libres para todos los departamentos; elimina o renombra los extras';
    END IF;
END $$;

UPDATE torre_residents r
SET dept_number = a.new_code
FROM (
    WITH letters(letter, code) AS (
        VALUES ('A', 101), ('B', 102), ('C', 201), ('D', 202), ('E', 203),
               ('F', 301), ('G', 302), ('H', 303), ('I', 304), ('J', 305)
    ),
    ranked AS (
        SELECT r.id,
               l.letter AS known_letter,
               l.code AS known_code,
               sum(CASE WHEN l.letter IS NULL THEN 1 ELSE 0 END) OVER (
                   ORDER BY r.id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS unknown_rn
        FROM torre_residents r
        LEFT JOIN letters l
          ON l.code::text = r.dept_number::text
          OR l.letter = upper(r.dept_number::text)
    ),
    free AS (
        SELECT l.letter,
               l.code,
               row_number() OVER (ORDER BY l.letter) AS rn
        FROM letters l
        WHERE NOT EXISTS (
            SELECT 1 FROM ranked r WHERE r.known_code = l.code
        )
    ),
    assigned AS (
        SELECT r.id,
               COALESCE(
                   r.known_code,
                   (SELECT f.code FROM free f WHERE f.rn = r.unknown_rn)
               ) AS new_code
        FROM ranked r
    )
    SELECT id, new_code FROM assigned
) a
WHERE r.id = a.id
  AND a.new_code IS NOT NULL
  AND r.dept_number::text <> a.new_code::text;

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
