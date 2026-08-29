# EML parser (reused, adapted)

Owner: Epic 1.

Per the master doc, this is reused tech, not written from scratch.

1. Clone https://github.com/05t3/EML-Parser
2. Copy the source into this folder (`backend/app/lib/eml_parser/`)
3. Adapt it as needed - strip anything you don't use, add an `__init__.py`
   that exposes whatever function(s) `services/parsing.py` needs to call
4. Keep it self-contained in this folder so it stays clearly "reused code we
   adapted" rather than getting mixed into your own `services/parsing.py` logic
