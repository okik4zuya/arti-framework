"""Updates for the dashboard: find out whether a newer release exists, show its notes, record that they were
read (phase 3a), then download and apply it, or go back to the previous version (phase 3b).

All logic lives in tools/arti-update (cli.py checks and downloads, updater.py swaps files in its own process);
this module wraps it for the server and keeps the progress the page polls. The dashboard never swaps its own
files: it starts updater.py, waits until the new version is unpacked and checked, and only then exits so the
updater can replace the code and start the dashboard again.
"""
import importlib.util
import os
import threading
import time

import license_gate

_spec = importlib.util.spec_from_file_location("arti_update_cli", license_gate.CODE_HOME / "tools" / "arti-update" / "cli.py")
arti_update = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(arti_update)

ACTIVE = ("downloading", "verifying", "restarting")
STATE = {"phase": "idle", "action": None, "version": None, "done": 0, "total": 0, "code": None, "message": None}
_lock = threading.Lock()


def stop_process():
    """Exit so the updater can replace the files. Tests replace this."""
    os._exit(0)


def _set(**kw):
    with _lock:
        STATE.update(kw)


def _view(state):
    current = arti_update.current_version()
    avail = state.get("available")
    if avail and arti_update.parse_version(avail.get("version")) <= arti_update.parse_version(current):
        avail = None   # an update that was just applied: the cached finding is stale until the next check
    return {
        "current": current,
        "channel": arti_update.update_channel(),
        "available": avail,
        "acked": bool(avail and state.get("acked") == avail.get("version")),
        "locked_newer": state.get("locked_newer"),
        "checked_at": state.get("checked_at"),
        "error": state.get("error"),
        "can_apply": bool(avail and avail.get("bundle") and not avail.get("requires_installer")),
        "backups": arti_update.list_backups(),
        "progress": progress(),
    }


def status():
    view = _view(arti_update.read_state())
    view["result"] = arti_update.read_result(consume=True)   # the outcome of the last apply/rollback is shown once
    return view


def check(force=True):
    return _view(arti_update.check(force=force))


def ack(version):
    ok, state = arti_update.ack(str(version or ""))
    return ok, _view(state)


def progress():
    with _lock:
        return dict(STATE)


def _fail(code, message):
    _set(phase="failed", code=code, message=message)


def _await_updater(proc):
    """Follow the updater until it has unpacked and checked the new version (then exit) or failed (stay alive)."""
    deadline = time.time() + 300
    while time.time() < deadline:
        res = arti_update.read_result()
        if res is not None and not res.get("ok"):
            arti_update.read_result(consume=True)
            return _fail(res.get("reason") or "error", res.get("message") or "The update did not finish.")
        prog = arti_update.read_progress() or {}
        if prog.get("phase") == "waiting":
            _set(phase="restarting")
            time.sleep(1.5)   # let the page show it and poll once more
            stop_process()
            return
        if proc.poll() is not None and prog.get("phase") not in ("waiting",):
            res = arti_update.read_result()
            if res is None:
                return _fail("error", "The updater stopped without a result. See .update/updater.log.")
        time.sleep(0.3)
    _fail("timeout", "The updater did not answer in time. See .update/updater.log.")


def _run(action, version):
    try:
        if action == "update":
            _set(phase="downloading", done=0, total=0)
            proc = arti_update.apply(version, opts=arti_update.dashboard_options(pid=os.getpid()),
                                     progress=lambda done, total: _set(done=done, total=total))
        else:
            _set(phase="verifying")
            proc = arti_update.rollback(version, opts=arti_update.dashboard_options(pid=os.getpid()))
        _set(phase="verifying")
        _await_updater(proc)
    except arti_update.UpdateFailure as e:
        _fail(e.code, str(e))
    except Exception as e:   # a thread must not die silently; the page shows this
        _fail("error", "The update stopped unexpectedly (%s)." % e)


def _start(action, version):
    with _lock:
        if STATE["phase"] in ACTIVE:
            raise arti_update.UpdateFailure("busy")
        STATE.update(phase="verifying" if action == "rollback" else "downloading", action=action, version=version,
                     done=0, total=0, code=None, message=None)
    threading.Thread(target=_run, args=(action, version), daemon=True).start()


def start_apply(version):
    """Check everything that can be checked now (read the notes, entitlement, bundle), then download and apply in a
    thread. Raises UpdateFailure for a refusal. The page follows progress()."""
    version = str(version or "")
    arti_update.preflight(version)
    _start("update", version)


def start_rollback(version=None):
    saved = arti_update.list_backups()
    version = version or (saved[0] if saved else None)
    if version is None or version not in saved:
        raise arti_update.UpdateFailure("no_backup")
    _start("rollback", version)


def dismiss():
    """The page showed a failure; go back to idle."""
    with _lock:
        if STATE["phase"] == "failed":
            STATE.update(phase="idle", code=None, message=None)


def check_in_background():
    """Once at server start: a silent check if the last one is older than a day and the license is usable."""
    def run():
        try:
            if not license_gate.is_locked() and arti_update.is_due():
                arti_update.check()
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()
