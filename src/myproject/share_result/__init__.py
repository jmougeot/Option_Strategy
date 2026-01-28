"""
Share Result Module
====================
Contains utilities for sharing results:
- email_utils: Generate Outlook emails with embedded images
- generate_pdf: Generate PDF reports
"""

from myproject.share_result.utils import (
    StrategyEmailData,
    EmailTemplateData,
)

from myproject.share_result.email_utils import (
    create_email_with_images,
)

from myproject.share_result.generate_pdf import (
    create_pdf_report,
)

from myproject.share_result.generate_email import (
    generate_html_email_from_template,
    open_outlook_with_email,
)

__all__ = [
    "StrategyEmailData",
    "EmailTemplateData",
    "create_email_with_images", 
    "create_pdf_report",
    "generate_html_email_from_template",
    "open_outlook_with_email",
]
