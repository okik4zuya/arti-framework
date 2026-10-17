"""Make Python's HTTPS trust the CA bundle that ships with `certifi`, on top of the Windows store.

On a clean Windows (the Sandbox, a fresh client PC) the certificate store can lack the root that signs a site's
chain, because Windows normally fetches missing roots only when a browser or the OS asks for them. Python's `ssl`
reads the store as it is, so `urllib` fails with "certificate verify failed" (seen on api.crossref.org in the
2026-10-17 Sandbox demo, which then took 14.6 minutes to export). `ssl.create_default_context()` also loads the
file named by SSL_CERT_FILE, so pointing that at certifi's bundle adds roots without removing any (a company
root in the Windows store keeps working). A value the user already set is left alone.

    from tls import use_certifi_bundle
    use_certifi_bundle()    # once, before the first request
"""
import os


def use_certifi_bundle():
    if os.environ.get("SSL_CERT_FILE"):
        return
    try:
        import certifi
    except ImportError:
        return
    path = certifi.where()
    if os.path.isfile(path):
        os.environ["SSL_CERT_FILE"] = path
