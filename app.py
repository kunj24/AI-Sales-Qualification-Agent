"""Streamlit UI for the AI Sales Qualification Agent."""
from __future__ import annotations

import json
import time
import uuid

import streamlit as st

from agent import AgentConfig, AgentError, extract_lead
from config import Settings, get_settings
from lead_state import merge_extraction_into_lead
from prompts import PromptSettings
from qualification import QualificationConfig, qualify_lead
from schemas import LeadRecord, LeadStatus
from storage import StorageError, get_mongodb_store

st.set_page_config(page_title="AI Sales Qualification Agent", page_icon="🎯", layout="wide")


def init_state() -> None:
    defaults = {
        "messages": [],
        "lead": LeadRecord(),
        "last_follow_up": None,
        "last_error": None,
        "last_diagnostic": None,
        "last_latency_seconds": None,
        "conversation_id": str(uuid.uuid4()),
        "last_storage_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()
settings = get_settings()
mongo_store = None
storage_init_error = None
if settings.mongodb_uri:
    try:
        mongo_store = get_mongodb_store(
            settings.mongodb_uri, settings.mongodb_database, settings.mongodb_collection
        )
    except StorageError as exc:
        storage_init_error = str(exc)

st.title("🎯 AI Sales Qualification Agent")
st.caption("A multi-turn Gemini-powered assistant that collects lead details and applies configurable Python qualification rules.")

with st.sidebar:
    st.header("Qualification settings")
    minimum_budget = st.number_input("Minimum budget (INR)", min_value=0.0, value=50000.0, step=5000.0)
    require_contact = st.checkbox("Require email or phone", value=True)
    require_timeline = st.checkbox("Require project timeline", value=True)
    require_requirements = st.checkbox("Require project requirements", value=True)

    st.divider()
    st.header("Prompt settings")
    role = st.text_input("Agent role", value="a helpful AI sales qualification assistant for a software-services company")
    style = st.text_input("Conversation style", value="professional, friendly, concise, and conversational")
    criteria = st.text_area(
        "Business context / criteria",
        value=("A lead must provide project requirements, budget, timeline, and at least one contact method. "
               "The Python qualification engine applies the final rules."),
        height=120,
    )
    follow_up_rules = st.text_area(
        "Follow-up rules",
        value=("Ask one concise, relevant question at a time. Prioritize contradictory information, then required "
               "missing details. Do not ask again for facts already supplied in the conversation."),
        height=100,
    )
    st.caption("Prompt settings guide the model. Qualification decisions remain controlled by the Python rules above.")

    st.divider()
    st.header("MongoDB storage")
    if not settings.mongodb_uri:
        st.info("MongoDB is not configured. Add MONGODB_URI to your .env file to save conversations and lead records.")
    elif mongo_store:
        st.success(f"Connected · {settings.mongodb_database}.{settings.mongodb_collection}")
        try:
            saved_conversations = mongo_store.list_conversations(limit=25)
            if saved_conversations:
                labels = {
                    item["_id"]: (
                        f"{item.get('customer_name') or 'Unnamed lead'} · "
                        f"{item.get('lead_status') or 'Not evaluated'} · "
                        f"{item.get('updated_at').strftime('%Y-%m-%d %H:%M') if item.get('updated_at') else 'No date'}"
                    )
                    for item in saved_conversations
                }
                selected_conversation = st.selectbox(
                    "Saved conversations", options=list(labels),
                    format_func=lambda value: labels.get(value, value),
                    key="saved_conversation_selector",
                )
                if st.button("Load selected conversation", use_container_width=True):
                    saved = mongo_store.load_conversation(selected_conversation)
                    if saved:
                        st.session_state.conversation_id = saved["_id"]
                        st.session_state.messages = saved.get("messages", [])
                        st.session_state.lead = LeadRecord.model_validate(saved.get("lead", {}))
                        st.session_state.last_follow_up = None
                        st.session_state.last_error = None
                        st.session_state.last_storage_error = None
                        st.rerun()
            else:
                st.caption("No saved conversations yet. Messages will be saved automatically.")
        except StorageError as exc:
            st.warning(str(exc))
    else:
        st.error(storage_init_error or "MongoDB connection unavailable.")

    if st.button("Start a new conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.lead = LeadRecord()
        st.session_state.last_follow_up = None
        st.session_state.last_error = None
        st.session_state.last_diagnostic = None
        st.session_state.last_latency_seconds = None
        st.session_state.last_storage_error = None
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

qualification_config = QualificationConfig(
    minimum_budget=float(minimum_budget),
    require_contact_method=require_contact,
    require_timeline=require_timeline,
    require_requirements=require_requirements,
)
prompt_settings = PromptSettings(
    role=role.strip() or "a helpful AI sales qualification assistant",
    style=style.strip() or "professional and concise",
    qualification_criteria=criteria.strip() or "Collect the information needed to evaluate the lead.",
    follow_up_rules=follow_up_rules.strip() or "Ask one concise follow-up question at a time.",
)

if not settings.gemini_api_key:
    st.warning("Gemini API key not found. Create a `.env` file beside `app.py` and set `GEMINI_API_KEY=your_key`. Get a key from Google AI Studio: https://aistudio.google.com/")

chat_col, record_col = st.columns([1.25, 1])
with chat_col:
    st.subheader("Conversation")
    st.caption(f"Conversation ID: {st.session_state.conversation_id}")
    if st.session_state.get("last_storage_error"):
        st.warning(f"MongoDB save failed: {st.session_state.last_storage_error}")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if st.session_state.last_latency_seconds is not None:
        st.caption(f"Last Gemini request: {st.session_state.last_latency_seconds:.2f} seconds")

    if st.session_state.last_error:
        st.error(st.session_state.last_error)
        if st.session_state.last_diagnostic:
            with st.expander("Troubleshooting details (do not share your API key)"):
                st.code(st.session_state.last_diagnostic)

    user_text = st.chat_input("Ask about a project or enter your lead details…", disabled=not bool(settings.gemini_api_key))
    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        request_started = time.perf_counter()
        try:
            agent_config = AgentConfig(settings=settings, prompt_settings=prompt_settings)
            with st.spinner("Checking lead details…"):
                extraction = extract_lead(
                    st.session_state.messages,
                    agent_config,
                    current_lead=st.session_state.lead,
                )
            st.session_state.last_latency_seconds = round(time.perf_counter() - request_started, 2)
            merged = merge_extraction_into_lead(st.session_state.lead, extraction)
            evaluated = qualify_lead(merged, qualification_config)
            st.session_state.lead = evaluated
            st.session_state.last_follow_up = extraction.follow_up_question
            st.session_state.last_error = None
            st.session_state.last_diagnostic = None

            # Show a short, customer-facing response, then one question if needed.
            reply = extraction.customer_reply.strip() if extraction.customer_reply else "Thanks. I’ll use those details to assess your project."
            if evaluated.lead_status == LeadStatus.NEEDS_MORE_INFORMATION:
                question = extraction.follow_up_question
                if not question:
                    missing = evaluated.missing_information
                    question = f"Could you share your {missing[0].lower()}?" if missing else "Could you clarify the details above?"
                reply = f"{reply}\n\n{question}"
            elif evaluated.lead_status == LeadStatus.QUALIFIED:
                reply = f"{reply}\n\nBased on the details provided, your lead currently meets the configured qualification criteria."
            else:
                reply = f"{reply}\n\nBased on the current criteria, this lead does not meet the configured budget requirement."
            st.session_state.messages.append({"role": "assistant", "content": reply})
            if mongo_store is not None:
                try:
                    mongo_store.save_conversation(
                        st.session_state.conversation_id,
                        st.session_state.messages,
                        evaluated,
                    )
                    st.session_state.last_storage_error = None
                except StorageError as storage_exc:
                    st.session_state.last_storage_error = str(storage_exc)
        except AgentError as exc:
            st.session_state.last_latency_seconds = round(time.perf_counter() - request_started, 2)
            st.session_state.last_error = str(exc)
            st.session_state.last_diagnostic = getattr(exc, "diagnostic", None)
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I couldn’t process that message right now. Please check the API setup and try again.",
            })
        st.rerun()

with record_col:
    lead = qualify_lead(st.session_state.lead, qualification_config)
    st.subheader("Lead qualification")
    status = lead.lead_status.value
    if lead.lead_status == LeadStatus.QUALIFIED:
        st.success(status)
    elif lead.lead_status == LeadStatus.UNQUALIFIED:
        st.error(status)
    else:
        st.info(status)
    st.write(lead.reason)

    st.markdown("**Lead details**")
    st.write(f"**Name:** {lead.customer_name or 'Not provided'}")
    st.write(f"**Email:** {lead.contact_details.email or 'Not provided'}")
    st.write(f"**Phone:** {lead.contact_details.phone or 'Not provided'}")
    st.write(f"**Requirements:** {', '.join(lead.requirements) if lead.requirements else 'Not provided'}")
    budget_text = f"{lead.budget.currency} {lead.budget.amount:,.2f}" if lead.budget.amount is not None else "Not provided"
    st.write(f"**Budget:** {budget_text}")
    st.write(f"**Timeline:** {lead.timeline or 'Not provided'}")

    if lead.missing_information:
        st.markdown("**Missing information**")
        for item in lead.missing_information:
            st.write(f"- {item}")
    if lead.contradictions:
        st.markdown("**Contradictions to clarify**")
        for item in lead.contradictions:
            st.write(f"- {item}")

    with st.expander("View structured lead JSON"):
        st.json(lead.model_dump(mode="json"))
    st.download_button(
        "Download lead JSON",
        data=json.dumps(lead.model_dump(mode="json"), indent=2, ensure_ascii=False),
        file_name="lead_record.json",
        mime="application/json",
        use_container_width=True,
    )
