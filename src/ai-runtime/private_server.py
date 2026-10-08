"""Start AIR's employment-capable listener with mandatory mTLS."""

from __future__ import annotations

import os
import ssl
from pathlib import Path

import uvicorn

from mtls_protocol import MutualTlsH11Protocol


def private_listener_config() -> uvicorn.Config:
    credentials = Path(os.environ["WAOOAW_WORKLOAD_CREDENTIALS"])
    workload = credentials / "workloads" / "ai-runtime"
    return uvicorn.Config(
        "main:app",
        host=os.getenv("AIR_PRIVATE_HOST", "0.0.0.0"),  # noqa: S104
        port=int(os.getenv("AIR_PRIVATE_PORT", "5444")),
        http=MutualTlsH11Protocol,
        ssl_keyfile=str(workload / "tls-key.pem"),
        ssl_certfile=str(workload / "tls-cert.pem"),
        ssl_ca_certs=str(credentials / "trust" / "ca-bundle.pem"),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
    )


def main() -> None:
    config = private_listener_config()
    if config.ssl is None:
        config.load()
    if config.ssl is None:
        raise RuntimeError("ADR-046 private listener requires TLS")
    config.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
