"""Tests for optional MongoDB storage configuration without a live database."""
import pytest

from storage import MongoDBStore, StorageError


def test_mongodb_store_requires_uri():
    with pytest.raises(StorageError, match="MONGODB_URI is not configured"):
        MongoDBStore("", "test_db")
