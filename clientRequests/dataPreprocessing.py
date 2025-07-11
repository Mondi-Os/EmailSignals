import re

def clean_email_body(text: str) -> str:
    if not text:
        return ""

    lower_text = text.lower()
    unsubscribe_index = lower_text.find("unsubscribe")
    if unsubscribe_index != -1:
        text = text[:unsubscribe_index]

    #TODO if more data preprocessing could be added would be great for data dimensionality/run time

    # Remove specific patterns and unwanted characters
    text = text.replace('\xa0', ' ')
    text = text.replace('-----------------------------------------------------------------------------', '-')
    text = text.replace('This Message originated outside your organization.', ' ')
    text = text.replace('\r', ' ')  # Handle carriage returns
    text = text.replace('\n', ' ')  # Flatten line breaks

    # Remove multiple spaces and strip edges
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()