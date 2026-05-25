import re
import pdfplumber


def extract_text_from_pdf(uploaded_file):
    text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text.strip()


def find_pattern(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def parse_order_text(text):
    return {
        "Booking Number": find_pattern(text, [
            r"Booking Number[:\s]+([A-Z0-9\-]+)",
            r"Booking[:\s]+([A-Z0-9\-]+)",
        ]),
        "Container Number": find_pattern(text, [
            r"Container Number[:\s]+([A-Z]{4}\d{7})",
            r"Container[:\s]+([A-Z]{4}\d{7})",
        ]),
        "Customer": find_pattern(text, [
            r"Customer[:\s]+(.+)",
            r"Consignee[:\s]+(.+)",
        ]),
        "Port": find_pattern(text, [
            r"Port[:\s]+(.+)",
            r"Terminal[:\s]+(.+)",
        ]),
        "Warehouse": find_pattern(text, [
            r"Warehouse[:\s]+(.+)",
            r"Delivery Location[:\s]+(.+)",
        ]),
        "Document Cutoff": find_pattern(text, [
            r"Document Cutoff[:\s]+(.+)",
            r"Doc Cutoff[:\s]+(.+)",
        ]),
    }