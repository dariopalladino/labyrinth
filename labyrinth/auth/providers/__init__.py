"""
Authentication providers for Labyrinth.
"""

from .azure_entra import AzureEntraAuthProvider

__all__ = [
    "AzureEntraAuthProvider",
]
