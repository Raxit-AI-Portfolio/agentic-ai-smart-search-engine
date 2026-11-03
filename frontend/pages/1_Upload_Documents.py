"""Manager-only document management page — new upload + existing document
list/edit/delete, all against the real shared-api /shared/documents endpoints.
"""

import sys
from pathlib import Path

# See frontend/Smart_Search.py's identical bootstrap: Streamlit multipage scripts each
# need the repo root on sys.path to import the root-level frontend/agentic_core
# packages — this page can also be the very first script run in a session.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

from frontend import documents_client
from frontend.session import init_session, is_logged_in

st.set_page_config(page_title="EFSSE — Upload Documents", layout="wide")
init_session()

st.title("Upload Documents")

if not is_logged_in():
    st.warning("Select a demo scenario on the Search page to log in first.")
    st.stop()

auth = st.session_state["auth"]
if auth.role != "manager":
    st.error("Manager access required. Load a manager scenario on the Search page.")
    st.stop()

_ROLES = ["customer", "worker", "manager"]

st.subheader("New document")
with st.form("upload_form", clear_on_submit=True):
    doc_name = st.text_input("Document Name")
    uploaded_file = st.file_uploader("Document Upload (.md only)", type=["md"])
    description = st.text_area("Description")
    allowed_roles = st.multiselect("Allowed roles", _ROLES, default=["customer"])
    submitted = st.form_submit_button("Save")

    if submitted:
        if not uploaded_file:
            st.error("Please choose a .md file to upload.")
        elif not allowed_roles:
            st.error("Select at least one allowed role.")
        else:
            filename = doc_name.strip() or uploaded_file.name
            if not filename.endswith(".md"):
                filename += ".md"
            try:
                result = documents_client.upload_document(
                    auth.token, filename, uploaded_file.getvalue(), allowed_roles, description
                )
                st.success(f"Ingested {result['chunks_ingested']} chunk(s) from {result['filename']}.")
            except Exception as exc:
                st.error(f"Upload failed: {exc}")

st.divider()
st.subheader("Existing documents")

try:
    documents = documents_client.list_documents(auth.token)
except Exception as exc:
    documents = []
    st.error(f"Could not load documents: {exc}")

if not documents:
    st.caption("No documents ingested yet.")
else:
    for doc in documents:
        cols = st.columns([3, 3, 2, 1, 1])
        cols[0].write(f"**{doc['filename']}**")
        cols[1].caption(doc.get("description") or doc.get("notes") or "(no description)")
        cols[2].caption(", ".join(doc["allowed_roles"]))

        if cols[3].button("Edit", key=f"edit_{doc['filename']}"):
            st.session_state["editing_document"] = doc["filename"]

        if cols[4].button("Delete", key=f"delete_{doc['filename']}"):
            try:
                documents_client.delete_document(auth.token, doc["filename"])
                st.rerun()
            except Exception as exc:
                st.error(f"Delete failed: {exc}")

        if st.session_state.get("editing_document") == doc["filename"]:
            with st.form(f"edit_form_{doc['filename']}"):
                st.caption(f"Editing {doc['filename']}")
                new_file = st.file_uploader("Reupload file (.md)", type=["md"], key=f"reupload_{doc['filename']}")
                new_notes = st.text_area("Description", value=doc.get("notes") or "", key=f"notes_{doc['filename']}")
                new_roles = st.multiselect("Allowed roles", _ROLES, default=doc["allowed_roles"], key=f"roles_{doc['filename']}")
                save_edit = st.form_submit_button("Save changes")

                if save_edit:
                    content = new_file.getvalue() if new_file else None
                    if content is None:
                        st.error("Re-ingestion requires re-uploading the file's content.")
                    else:
                        try:
                            documents_client.upload_document(auth.token, doc["filename"], content, new_roles, new_notes)
                            st.session_state.pop("editing_document", None)
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Update failed: {exc}")
