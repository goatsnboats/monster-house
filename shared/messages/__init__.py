"""Message payloads, one module per ICD, generated from the ICDs (ADR 0003).

    eye_commands    ICD-001  brain -> eyes: look, expression, blink, theme; eye status
    radar_targets   ICD-002  radar -> brain: target values and count (plain text)
    clips           ICD-003  Falcon Player -> brain: player status, playlist playing
    phone_page      ICD-004  phone page <-> brain: state, buttons, mood

Every module except codec.py is written by `python -m tools.reqs.check`; don't edit
them by hand. Use them like this:

    from shared.messages import eye_commands as eyes

    payload = eyes.encode("blink", eyes.Blink(ms=180))   # b'{"ms": 180}'
    message = eyes.decode("blink", payload)              # Blink(ms=180), or None if bad
"""
