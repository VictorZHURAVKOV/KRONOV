"""Tools which the Claude agent can call."""
from .catalog import CATALOG, get_model_info, suggest_model
from .calculator import calculate_price
from .crm import save_contact, log_to_crm, handoff_to_alena
from .pdf_gen import generate_kp_pdf, generate_contract_pdf

__all__ = [
    "CATALOG",
    "get_model_info",
    "suggest_model",
    "calculate_price",
    "save_contact",
    "log_to_crm",
    "handoff_to_alena",
    "generate_kp_pdf",
    "generate_contract_pdf",
]
