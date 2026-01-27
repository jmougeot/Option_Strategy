"""
Share Result Module
====================
Contient les utilitaires pour partager les résultats :
- email_utils: Génération d'emails Outlook avec images intégrées
- pdf_report: Génération de rapports PDF
"""

from myproject.share_result.email_utils import (
    StrategyEmailData,
    create_email_with_images,
    create_pdf_report,
    generate_mailto_link,
)

__all__ = [
    "StrategyEmailData",
    "create_email_with_images", 
    "create_pdf_report",
    "generate_mailto_link",
]
