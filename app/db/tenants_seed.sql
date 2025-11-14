BEGIN;

INSERT INTO tenants (id, name, domain, timezone, locale) VALUES
('soft-tech',  'Soft-Tech',   'soft-innova.com',     'America/Santiago', 'es-CL'),
('annie',      'Annie-AI',    'annie-ai.app',        'America/Santiago', 'es-CL'),
('vicky-ai',   'Vicky-AI',    'vicky-ai.cl',         'America/Santiago', 'es-CL'),
('demo-annie', 'DEMO-Annie',  'demo.annie-ai.app',   'America/Santiago', 'es-CL'),
('telco-sa',   'TELCO SA',    'telcosa.cl',          'America/Santiago', 'es-CL')
ON CONFLICT (id) DO UPDATE
SET name=EXCLUDED.name, domain=EXCLUDED.domain, timezone=EXCLUDED.timezone, locale=EXCLUDED.locale;

COMMIT;
