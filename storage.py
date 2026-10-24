"""Optional MongoDB persistence for lead records and chat conversations."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from schemas import LeadRecord


class StorageError(RuntimeError):
    """Raised when a configured MongoDB store cannot be used."""


class MongoDBStore:
    def __init__(self, uri: str, database_name: str, collection_name: str = "conversations"):
        if not uri.strip():
            raise StorageError("MONGODB_URI is not configured.")
        try:
            from pymongo import MongoClient
            from pymongo.errors import PyMongoError
        except ImportError as exc:
            raise StorageError("pymongo is not installed. Run: pip install -r requirements.txt") from exc

        self._pymongo_error = PyMongoError
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=2500, connectTimeoutMS=2500)
            self.client.admin.command("ping")
            self.collection = self.client[database_name][collection_name]
            self.collection.create_index("updated_at")
        except Exception as exc:
            raise StorageError(f"Could not connect to MongoDB: {exc}") from exc

    def save_conversation(self, conversation_id: str, messages: list[dict[str, str]], lead: LeadRecord) -> None:
        now = datetime.now(timezone.utc)
        document = {
            "_id": conversation_id,
            "messages": messages,
            "lead": lead.model_dump(mode="json"),
            "customer_name": lead.customer_name,
            "lead_status": lead.lead_status.value,
            "budget_amount": lead.budget.amount,
            "budget_currency": lead.budget.currency,
            "updated_at": now,
        }
        try:
            self.collection.update_one(
                {"_id": conversation_id},
                {"$set": document, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        except self._pymongo_error as exc:
            raise StorageError(f"Could not save conversation to MongoDB: {exc}") from exc

    def list_conversations(self, limit: int = 25) -> list[dict[str, Any]]:
        try:
            cursor = self.collection.find(
                {}, {"messages": 0, "lead": 0}
            ).sort("updated_at", -1).limit(limit)
            return list(cursor)
        except self._pymongo_error as exc:
            raise StorageError(f"Could not list saved conversations: {exc}") from exc

    def load_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        try:
            return self.collection.find_one({"_id": conversation_id})
        except self._pymongo_error as exc:
            raise StorageError(f"Could not load saved conversation: {exc}") from exc


@lru_cache(maxsize=2)
def get_mongodb_store(uri: str, database_name: str, collection_name: str = "conversations") -> MongoDBStore:
    """Reuse one MongoDB client across Streamlit reruns."""
    return MongoDBStore(uri, database_name, collection_name)
