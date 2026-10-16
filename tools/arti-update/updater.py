"""arti-update updater: put a downloaded release in place, check it, and undo everything if it does not work.

Runs as its own process from a COPY under .update/run/ (together with bundle.py, license.py, paths.py and
pubkeys.json), so it is never one of the files it swaps. It trusts nothing from the process that started it:
the signed manifest, the zip size and sha256 are checked again here.

    updater.py --home H --code C --zip Z --doc DOC.json --version NEW --from OLD [options]
    updater.py --rollback VERSION --home H --code C [options]

Options: --pid PID (dashboard to stop), --relaunch-json '["cmd", ...]' --relaunch-cwd DIR (start it again),
--ping-url URL (health check after the restart), --smoke-json '["cmd", ...]' (must exit 0 after the swap),
--claude-skills DIR (where skill junctions live, default ~/.claude/skills), --pubkeys FILE, --wait-s, --health-s.

Order for an update: verify -> unpack to .update/staging (the dashboard is still running) -> phase "waiting"
(the dashboard sees it and exits) -> back up replaced items to .backup/<old version>/ and memory/arti.db to
arti.db.bak -> swap item by item with renames (directories first, VERSION last; one failure puts back what was
swapped) -> skill junctions -> relaunch and health check. If the new version does not come up, the old code and
database are put back and the old dashboard is started again. The outcome is written to .update/result.json.
User content (memory/, license.json, mcp-keys.json, voice-profiles/ ...) is never an update item and is never touched.
"""
import argparse
import http.client
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "_shared"))
import bundle  # noqa: E402
import license as lic  # noqa: E402

KEEP_BACKUPS = 2
LOCK_STALE_S = 30 * 60
WIN = sys.platform == "win32"


class UpdateError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ---- small helpers -------------------------------------------------------------------------------

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_version(s):
    try:
        return tuple(int(p) for p in str(s).split("."))
    except ValueError:
        return (0,)


class Ctx:
    def __init__(self, a):
        self.home = os.path.abspath(a.home)
        self.code = os.path.abspath(a.code)
        self.update_dir = os.path.join(self.home, ".update")
        self.backup_root = os.path.join(self.home, ".backup")
        self.staging = os.path.join(self.update_dir, "staging")
        self.discard = os.path.join(self.update_dir, "discard")
        links = a.claude_skills or os.environ.get("ARTI_CLAUDE_SKILLS")   # the env override is for tests
        self.skills_link_dir = os.path.abspath(links) if links else os.path.join(os.path.expanduser("~"), ".claude", "skills")
        self.pid = a.pid
        self.relaunch = json.loads(a.relaunch_json) if a.relaunch_json else None
        self.relaunch_cwd = a.relaunch_cwd
        self.ping_url = a.ping_url
        self.smoke = json.loads(a.smoke_json) if a.smoke_json else None
        self.wait_s = a.wait_s
        self.health_s = a.health_s
        self.child = None   # the relaunched dashboard, so a failed health check can stop it again

    def path(self, *p):
        return os.path.join(self.update_dir, *p)


def log(ctx, msg):
    try:
        os.makedirs(ctx.update_dir, exist_ok=True)
        with open(ctx.path("updater.log"), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (now_iso(), msg))
    except OSError:
        pass


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for attempt in range(40):   # on Windows the dashboard may have the file open for reading at this very moment
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(0.05)


def phase(ctx, name, **extra):
    log(ctx, "phase " + name)
    try:
        write_json(ctx.path("progress.json"), dict(phase=name, at=now_iso(), **extra))
    except OSError as e:   # the progress file is advisory; never stop an update for it
        log(ctx, "could not write progress.json: %s" % e)


def write_result(ctx, ok, **fields):
    write_json(ctx.path("result.json"), dict(ok=ok, at=now_iso(), **fields))


def rmtree(path):
    def onerr(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, onerror=onerr)
    elif os.path.lexists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def rename_retry(src, dst, tries=3):
    last = None
    for i in range(tries):
        try:
            os.rename(src, dst)
            return
        except OSError as e:
            last = e
            time.sleep(0.4 * (i + 1))
    raise last


# ---- processes ----------------------------------------------------------------------------------

def pid_alive(pid):
    if not pid:
        return False
    if WIN:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x00100000, False, int(pid))   # SYNCHRONIZE
        if not h:
            return False
        try:
            return k.WaitForSingleObject(h, 0) == 0x102   # WAIT_TIMEOUT: still running
        finally:
            k.CloseHandle(h)
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def kill_tree(pid):
    if not pid:
        return
    if WIN:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.kill(int(pid), 15)
        except OSError:
            pass


def stop_dashboard(ctx):
    if not ctx.pid:
        return
    deadline = time.time() + ctx.wait_s
    while pid_alive(ctx.pid) and time.time() < deadline:
        time.sleep(0.25)
    if pid_alive(ctx.pid):
        log(ctx, "dashboard pid %s did not exit in %ss; killing it" % (ctx.pid, ctx.wait_s))
        kill_tree(ctx.pid)
        for _ in range(40):
            if not pid_alive(ctx.pid):
                break
            time.sleep(0.25)
        if pid_alive(ctx.pid):
            raise UpdateError("still_running", "The ARTi window could not be closed. Close it by hand and try again.")


def launch(ctx):
    if not ctx.relaunch:
        return None
    flags = 0
    kw = {}
    if WIN:
        flags = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW
    else:
        kw["start_new_session"] = True
    return subprocess.Popen(ctx.relaunch, cwd=ctx.relaunch_cwd or None, creationflags=flags, close_fds=True,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)


def wait_ping(url, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException):
            pass
        time.sleep(0.5)
    return False


def healthy(ctx):
    """The new version counts as working when its smoke command exits 0 and the relaunched dashboard answers."""
    if ctx.smoke:
        r = subprocess.run(ctx.smoke, capture_output=True, timeout=60)
        if r.returncode != 0:
            log(ctx, "smoke command failed (%s): %s" % (r.returncode, r.stderr.decode("utf-8", "replace")[-400:]))
            return False
    if ctx.relaunch:
        ctx.child = launch(ctx)
        if ctx.ping_url and not wait_ping(ctx.ping_url, ctx.health_s):
            log(ctx, "the relaunched dashboard did not answer %s in %ss" % (ctx.ping_url, ctx.health_s))
            return False
    return True


def stop_child(ctx):
    if ctx.child is not None:
        kill_tree(ctx.child.pid)
        try:
            ctx.child.wait(timeout=10)
        except Exception:
            pass
        ctx.child = None
        time.sleep(0.5)


# ---- verification --------------------------------------------------------------------------------

def verify_doc(doc, version, pubkeys_path):
    try:
        manifest, sig, kid = doc["manifest"], doc["sig"], doc["kid"]
        pub = lic.load_pubkeys(pubkeys_path).get("release", {}).get(kid)
    except (KeyError, TypeError, OSError, ValueError):
        raise UpdateError("bad_manifest", "The update information is damaged.")
    if pub is None or not lic.verify_signature(manifest, sig, pub):
        raise UpdateError("bad_manifest", "The update information could not be verified and was not applied.")
    if manifest.get("version") != version:
        raise UpdateError("bad_manifest", "The update information is for another version.")
    b = manifest.get("bundle")
    if not isinstance(b, dict) or not all(k in b for k in ("sha256", "size", "items")):
        raise UpdateError("no_bundle", "This release has no in-app update. Use the installer.")
    return manifest


def check_zip_file(path, b):
    if not os.path.isfile(path):
        raise UpdateError("bad_download", "The downloaded file is missing.")
    if os.path.getsize(path) != b["size"] or bundle.sha256_file(path) != b["sha256"]:
        raise UpdateError("bad_download", "The downloaded file does not match the signed release. Nothing was changed.")


# ---- backup, swap, undo --------------------------------------------------------------------------

def backup_database(ctx, backup_dir):
    db = os.path.join(ctx.home, "memory", "arti.db")
    if not os.path.isfile(db):
        return
    dst = os.path.join(backup_dir, "arti.db.bak")
    src = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    try:
        out = sqlite3.connect(dst)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()


def restore_database(ctx, backup_dir):
    bak = os.path.join(backup_dir, "arti.db.bak")
    db = os.path.join(ctx.home, "memory", "arti.db")
    if not os.path.isfile(bak):
        return
    for suffix in ("-wal", "-shm", "-journal"):
        try:
            os.remove(db + suffix)
        except OSError:
            pass
    shutil.copyfile(bak, db)


def put_aside(ctx, item, strict=False):
    """Move whatever is at code/<item> out of the way (into .update/discard). Returns where it went, or None.
    Unless strict, a copy that cannot be moved is deleted instead."""
    cur = os.path.join(ctx.code, item)
    if not os.path.lexists(cur):
        return None
    os.makedirs(ctx.discard, exist_ok=True)
    dst = os.path.join(ctx.discard, "%s.%d" % (item, int(time.time() * 1000)))
    try:
        rename_retry(cur, dst)
        return dst
    except OSError:
        if strict:
            raise
        rmtree(cur)
        return None


def swap_in(ctx, items, backup_dir):
    """Replace each item with its staged copy. Returns nothing; on failure everything done so far is undone."""
    done = []
    try:
        for item in bundle.swap_order(items):
            cur = os.path.join(ctx.code, item)
            new = os.path.join(ctx.staging, item)
            had_old = os.path.lexists(cur)
            if had_old:
                rename_retry(cur, os.path.join(backup_dir, item))
            done.append((item, had_old, False))
            rename_retry(new, cur)
            done[-1] = (item, had_old, True)
            log(ctx, "swapped " + item)
    except OSError as e:
        log(ctx, "swap failed on %s: %s" % (done[-1][0] if done else "?", e))
        undo_swap(ctx, done, backup_dir)
        raise UpdateError("locked", "Some ARTi files are in use, so nothing was changed. Close other ARTi windows and "
                                    "Claude Code sessions that use ARTi, then try again.")


def undo_swap(ctx, done, backup_dir):
    for item, had_old, placed in reversed(done):
        if placed:
            put_aside(ctx, item)
        if had_old:
            src = os.path.join(backup_dir, item)
            if os.path.lexists(src):
                try:
                    rename_retry(src, os.path.join(ctx.code, item))
                except OSError as e:
                    log(ctx, "could not put back %s: %s" % (item, e))


def restore_from_backup(ctx, backup_dir, strict=False):
    """Put every item in backup_dir back in place (current copy goes aside). VERSION last.
    strict: a failure puts back the items already restored and re-raises, so a rollback is all or nothing."""
    items = [i for i in os.listdir(backup_dir) if i in bundle.UPDATE_ITEMS]
    done = []   # (item, where the replaced copy went)
    try:
        for item in bundle.swap_order(items):
            aside = put_aside(ctx, item, strict=strict)
            try:
                rename_retry(os.path.join(backup_dir, item), os.path.join(ctx.code, item))
            except OSError:
                if aside:
                    rename_retry(aside, os.path.join(ctx.code, item))
                raise
            done.append((item, aside))
            log(ctx, "restored " + item)
    except OSError:
        if strict:
            for item, aside in reversed(done):
                try:
                    rename_retry(os.path.join(ctx.code, item), os.path.join(backup_dir, item))
                    if aside:
                        rename_retry(aside, os.path.join(ctx.code, item))
                except OSError as e:
                    log(ctx, "could not undo the rollback of %s: %s" % (item, e))
        raise
    return items


def prune_backups(ctx):
    if not os.path.isdir(ctx.backup_root):
        return
    versions = sorted((d for d in os.listdir(ctx.backup_root) if os.path.isdir(os.path.join(ctx.backup_root, d))),
                      key=parse_version, reverse=True)
    for old in versions[KEEP_BACKUPS:]:
        rmtree(os.path.join(ctx.backup_root, old))


# ---- skill junctions -----------------------------------------------------------------------------

def _is_link(path):
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if WIN:
        return bool(getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return stat.S_ISLNK(st.st_mode)


def _link_target(path):
    try:
        t = os.readlink(path)
    except OSError:
        return None
    if t.startswith("\\\\?\\"):
        t = t[4:]
    return os.path.normcase(os.path.abspath(t))


def relink_skills(ctx):
    """Every skill folder gets a link in the Claude skills folder; links to skills that no longer exist are removed.
    A real folder (an earlier copy fallback) is left alone. Existing links keep working across a swap because they
    point at the path, which is why only new and removed skills need work."""
    skills = os.path.join(ctx.code, "skills")
    link_dir = ctx.skills_link_dir
    wanted = {}
    if os.path.isdir(skills):
        for name in sorted(os.listdir(skills)):
            if os.path.isdir(os.path.join(skills, name)):
                wanted[name] = os.path.normcase(os.path.abspath(os.path.join(skills, name)))
    # orphans: links that point into our skills folder at something that is gone
    if os.path.isdir(link_dir):
        root = os.path.normcase(os.path.abspath(skills)) + os.sep
        for name in os.listdir(link_dir):
            p = os.path.join(link_dir, name)
            if _is_link(p):
                t = _link_target(p)
                if t and t.startswith(root) and not os.path.exists(p):
                    _unlink(p)
                    log(ctx, "removed dangling skill link " + name)
    os.makedirs(link_dir, exist_ok=True)
    for name, target in wanted.items():
        p = os.path.join(link_dir, name)
        if _is_link(p):
            if _link_target(p) == target and os.path.exists(p):
                continue
            _unlink(p)
        elif os.path.lexists(p):
            log(ctx, "skill %s is a real folder in the Claude skills folder; left as it is" % name)
            continue
        if WIN:
            r = subprocess.run(["cmd", "/c", "mklink", "/J", p, os.path.join(skills, name)], capture_output=True)
            if r.returncode != 0:
                log(ctx, "mklink failed for %s: %s" % (name, r.stdout.decode("utf-8", "replace").strip()))
        else:
            os.symlink(os.path.join(skills, name), p)
        log(ctx, "linked skill " + name)


def _unlink(p):
    try:
        os.rmdir(p) if WIN else os.remove(p)   # rmdir on a junction removes the link, never the target
    except OSError:
        pass


# ---- the two operations --------------------------------------------------------------------------

def acquire_lock(ctx):
    os.makedirs(ctx.update_dir, exist_ok=True)
    lock = ctx.path("updater.lock")
    try:
        if time.time() - os.path.getmtime(lock) > LOCK_STALE_S:
            os.remove(lock)
    except OSError:
        pass
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise UpdateError("busy", "Another update is already running.")
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return lock


def installed_version(code):
    try:
        with open(os.path.join(code, "VERSION"), encoding="utf-8") as f:
            return bundle.framework_version(f.read()) or "0.0.0"
    except OSError:
        return "0.0.0"


def do_update(ctx, a):
    old = a.from_version
    new = a.version
    with open(a.doc, encoding="utf-8") as f:
        doc = json.load(f)
    phase(ctx, "verifying")
    manifest = verify_doc(doc, new, a.pubkeys)
    b = manifest["bundle"]
    if parse_version(new) <= parse_version(installed_version(ctx.code)):
        raise UpdateError("not_newer", "That version is not newer than the installed one.")
    check_zip_file(a.zip, b)
    try:
        zf, items = bundle.open_validated(a.zip, new)
    except bundle.BundleError as e:
        raise UpdateError("bad_bundle", "The update package was rejected: %s. Nothing was changed." % e)
    try:
        if sorted(items) != sorted(b["items"]):
            raise UpdateError("bad_bundle", "The update package does not match the signed release. Nothing was changed.")
        phase(ctx, "unpacking")
        rmtree(ctx.staging)
        os.makedirs(ctx.staging)
        bundle.extract(zf, ctx.staging)
    finally:
        zf.close()

    phase(ctx, "waiting")   # the dashboard sees this, answers its last request and exits
    stop_dashboard(ctx)

    phase(ctx, "swapping")
    backup_dir = os.path.join(ctx.backup_root, old)
    swapped = False
    try:
        rmtree(backup_dir)
        os.makedirs(backup_dir)
        backup_database(ctx, backup_dir)
        swap_in(ctx, items, backup_dir)   # a failure here has already put back what it moved
        swapped = True
        relink_skills(ctx)
        phase(ctx, "checking")
        if not healthy(ctx):
            raise UpdateError("unhealthy", "Version %s did not start correctly, so version %s was put back." % (new, old))
    except BaseException:
        stop_child(ctx)
        if swapped:
            restore_old_after_failure(ctx, backup_dir)
        else:
            relaunch_old(ctx)   # the dashboard was already stopped; bring the untouched old one back
        rmtree(backup_dir)      # everything is back in place; a leftover folder would offer a pointless rollback
        raise
    prune_backups(ctx)
    rmtree(ctx.staging)
    rmtree(ctx.discard)
    rmtree(ctx.path("download"))
    write_result(ctx, True, action="update", **{"from": old, "to": new})


def restore_old_after_failure(ctx, backup_dir):
    log(ctx, "restoring version after a failed update")
    try:
        restore_from_backup(ctx, backup_dir)
    except OSError as e:
        log(ctx, "restore from backup failed: %s" % e)
    try:
        restore_database(ctx, backup_dir)
    except OSError as e:
        log(ctx, "database restore failed: %s" % e)
    relink_skills(ctx)
    relaunch_old(ctx)


def relaunch_old(ctx):
    try:
        ctx.child = launch(ctx)
    except OSError as e:
        log(ctx, "could not start the dashboard again: %s" % e)


def do_rollback(ctx, a):
    ver = a.rollback
    backup_dir = os.path.join(ctx.backup_root, ver)
    if not os.path.isdir(backup_dir):
        raise UpdateError("no_backup", "There is no saved copy of version %s." % ver)
    current = installed_version(ctx.code)
    phase(ctx, "waiting")
    stop_dashboard(ctx)
    phase(ctx, "swapping")
    try:
        restore_from_backup(ctx, backup_dir, strict=True)
    except OSError as e:
        relaunch_old(ctx)
        raise UpdateError("locked", "Some ARTi files are in use, so nothing was changed. Close other ARTi windows and Claude Code sessions, then try again. (%s)" % e)
    relink_skills(ctx)
    phase(ctx, "checking")
    if not healthy(ctx):
        stop_child(ctx)
        raise UpdateError("unhealthy", "Version %s did not start after the rollback." % ver)
    rmtree(backup_dir)
    rmtree(ctx.discard)
    write_result(ctx, True, action="rollback", **{"from": current, "to": ver})


def main(argv=None):
    ap = argparse.ArgumentParser(prog="updater")
    ap.add_argument("--home", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--zip")
    ap.add_argument("--doc")
    ap.add_argument("--version")
    ap.add_argument("--from", dest="from_version")
    ap.add_argument("--rollback")
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--relaunch-json")
    ap.add_argument("--relaunch-cwd")
    ap.add_argument("--ping-url")
    ap.add_argument("--smoke-json")
    ap.add_argument("--claude-skills")
    ap.add_argument("--pubkeys", default=os.path.join(HERE, "pubkeys.json") if os.path.exists(os.path.join(HERE, "pubkeys.json")) else None)
    ap.add_argument("--wait-s", type=float, default=20)
    ap.add_argument("--health-s", type=float, default=30)
    a = ap.parse_args(argv)
    ctx = Ctx(a)
    if not a.rollback and not (a.zip and a.doc and a.version and a.from_version):
        ap.error("an update needs --zip --doc --version --from")
    try:
        lock = acquire_lock(ctx)
    except UpdateError as e:
        print(e.message, file=sys.stderr)
        return 2
    try:
        try:
            os.remove(ctx.path("result.json"))
        except OSError:
            pass
        log(ctx, "start %s" % (("rollback to " + a.rollback) if a.rollback else ("update %s -> %s" % (a.from_version, a.version))))
        try:
            (do_rollback if a.rollback else do_update)(ctx, a)
            phase(ctx, "done")
            return 0
        except UpdateError as e:
            log(ctx, "failed [%s] %s" % (e.code, e.message))
            write_result(ctx, False, action="rollback" if a.rollback else "update", reason=e.code, message=e.message,
                         **{"from": a.from_version or installed_version(ctx.code), "to": a.version or a.rollback})
            phase(ctx, "failed")
            return 1
        except Exception as e:   # never leave without a result the dashboard can show
            log(ctx, "crashed: %r" % (e,))
            write_result(ctx, False, action="rollback" if a.rollback else "update", reason="error",
                         message="The update stopped unexpectedly (%s). See .update/updater.log." % e,
                         **{"from": a.from_version or installed_version(ctx.code), "to": a.version or a.rollback})
            phase(ctx, "failed")
            return 1
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
