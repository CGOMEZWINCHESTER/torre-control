UPDATE torre_announcements
SET title = replace(title, 'Torre Roble', 'Torre 40'),
    body = replace(body, 'Torre Roble', 'Torre 40'),
    updated_at = now()
WHERE title LIKE '%Torre Roble%' OR body LIKE '%Torre Roble%';
