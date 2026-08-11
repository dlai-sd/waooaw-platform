"""Start the WBE Relationship Workspace private listener with mandatory mTLS."""

# Implements: ADR-046 sections 3.1, 3.2, 4.1, and 10.1
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

import os
import ssl
from pathlib import Path

import uvicorn
from mtls_protocol import MutualTlsH11Protocol


def private_listener_config() -> uvicorn.Config:
    credentials = Path(os.environ["WAOOAW_WORKLOAD_CREDENTIALS"])
    workload = credentials / "workloads" / "billing-engine"
    return uvicorn.Config(
        "main:create_app", factory=True, host=os.getenv("WBE_PRIVATE_HOST", "0.0.0.0"),  # noqa: S104
        port=int(os.getenv("WBE_PRIVATE_PORT", "5444")), http=MutualTlsH11Protocol,
        ssl_keyfile=str(workload / "tls-key.pem"), ssl_certfile=str(workload / "tls-cert.pem"),
        ssl_ca_certs=str(credentials / "trust" / "ca-bundle.pem"), ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER)


def main() -> None:
    config = private_listener_config()
    config.load()
    if config.ssl is None:
        raise RuntimeError("ADR-046 private listener requires TLS")
    config.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()