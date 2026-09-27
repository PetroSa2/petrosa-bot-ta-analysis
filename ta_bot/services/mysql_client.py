"""Deprecated compatibility alias; use :class:`DataManagerGateway`."""

from .data_manager_gateway import DataManagerGateway

MySQLClient = DataManagerGateway

__all__ = ["MySQLClient"]
