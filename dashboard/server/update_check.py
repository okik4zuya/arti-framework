"""Update check for the dashboard (phase 3a): find out whether a newer release exists, show its notes,
record that they were read. Applying an update is a later phase; today the researcher runs the newer
installer. All logic lives in tools/arti-update/cli.py; this module only wraps it for the server.
"""
import importlib.util
import threading

import license_gate

_spec = importlib.util.spec_from_file_location("arti_update_cli", license_gate.CODE_HOME / "tools" / "arti-update" / "cli.py")
arti_update = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(arti_update)


def _view(state):
    avail = state.get("available")
    return {
        "current": state.get("current") or arti_update.current_version(),
        "available": avail,
        "acked": bool(avail and state.get("acked") == avail.get("version")),
        "locked_newer": state.get("locked_newer"),
        "checked_at": state.get("checked_at"),
        "error": state.get("error"),
    }


def status():
    return _view(arti_update.read_state())


def check(force=True):
    return _view(arti_update.check(force=force))


def ack(version):
    ok, state = arti_update.ack(str(version or ""))
    return ok, _view(state)


def check_in_background():
    """Once at server start: a silent check if the last one is older than a day and the license is usable."""
    def run():
        try:
            if not license_gate.is_locked() and arti_update.is_due():
                arti_update.check()
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()
