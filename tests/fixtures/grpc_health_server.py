#!/usr/bin/env python3
"""Minimal gRPC health server for Professional Runtime lifecycle tests."""

from __future__ import annotations

from concurrent import futures

import grpc


def check(_request: bytes, _context: grpc.ServicerContext) -> bytes:
    return b"\x08\x01"


def main() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    handler = grpc.method_handlers_generic_handler(
        "grpc.health.v1.Health",
        {
            "Check": grpc.unary_unary_rpc_method_handler(
                check,
                request_deserializer=lambda payload: payload,
                response_serializer=lambda payload: payload,
            )
        },
    )
    server.add_generic_rpc_handlers((handler,))
    server.add_insecure_port("0.0.0.0:5002")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    main()
