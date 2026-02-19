"""
PDF generation module for Options Strategy.
Generates PDF reports with the new template format.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from myproject.share_result.utils import EmailTemplateData


def generate_pdf_report(
    template_data: EmailTemplateData,
    images: Optional[List[str]] = None,
) -> Optional[bytes]:
    """
    Generate a PDF report with the new template format.
    Single pipeline for PDF generation.
    
    Structure:
    - Page 1: Payoff diagram (full page)
    - Page 2: Top 10 summary (full page)
    - Page 3: Parameters and best strategies
    
    Args:
        template_data: EmailTemplateData with all parameters
        images: List of image paths [payoff_diagram, top10_summary]
    
    Returns:
        bytes of the PDF or None if error
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        import io
    except ImportError:
        print("[PDF] reportlab is not installed. Install with: pip install reportlab")
        return None
    
    images = images or []
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        leftMargin=1.5*cm, 
        rightMargin=1.5*cm,
        topMargin=1.5*cm, 
        bottomMargin=1.5*cm
    )
    
    page_width = landscape(A4)[0] - 3*cm
    page_height = landscape(A4)[1] - 3*cm
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_CENTER,
        spaceAfter=15,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#2c5282'),
        spaceBefore=10,
        spaceAfter=4,
    )
    param_style = ParagraphStyle(
        'ParamStyle',
        parent=styles['Normal'],
        fontSize=9,
        spaceBefore=2,
        spaceAfter=2,
    )
    image_title_style = ParagraphStyle(
        'ImageTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    strategy_style = ParagraphStyle(
        'StrategyStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=6,
        spaceAfter=6,
    )
    
    elements = []

    # =========================================================================
    # PAGE 1: PAYOFF DIAGRAM (full page)
    # =========================================================================
    if len(images) > 0 and os.path.exists(images[0]):
        elements.append(Paragraph("Payoff Diagram - Best Strategy", image_title_style))
        elements.append(Spacer(1, 10))
        
        try:
            img_width = page_width * 0.95
            img_height = page_height * 0.85
            img = RLImage(images[0], width=img_width, height=img_height)
            elements.append(img)
        except Exception as e:
            print(f"[PDF] Error loading payoff image: {e}")
        
        elements.append(PageBreak())
    
    # =========================================================================
    # PAGE 2: TOP 10 SUMMARY (full page)
    # =========================================================================
    if len(images) > 1 and os.path.exists(images[1]):
        elements.append(Paragraph("Top 10 Strategies Comparison", image_title_style))
        elements.append(Spacer(1, 10))
        
        try:
            img_width = page_width * 0.95
            img_height = page_height * 0.85
            img = RLImage(images[1], width=img_width, height=img_height)
            elements.append(img)
        except Exception as e:
            print(f"[PDF] Error loading summary image: {e}")
        
        elements.append(PageBreak())
    
    # =========================================================================
    # PAGE 3: PARAMETERS AND BEST STRATEGIES
    # =========================================================================
    
    # Title
    underlying = template_data.underlying or "Options"
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    elements.append(Paragraph(f"Options Strategy Report - {underlying}", title_style))
    elements.append(Paragraph(date_str, subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Criteria Section
    elements.append(Paragraph("Search Criteria", section_style))
    
    criteria_data = [
        ["TARGET:", template_data.target_description],
        ["TAIL RISK:", template_data.tail_risk_description],
        ["MAX RISK:", template_data.max_risk_description],
        ["MAX LEGS:", f"{template_data.max_legs} legs ({template_data.max_legs} strikes)"],
        ["STRIKES SCREENED:", template_data.strikes_screened_description],
        ["DELTA:", template_data.delta_description],
        ["PREMIUM SPENT MAX:", template_data.premium_max_description],
        ["MAX LOSS:", template_data.max_loss_description],
        ["WEIGHTING:", template_data.weighting_description],
    ]
    
    criteria_table = Table(criteria_data, colWidths=[4*cm, 16*cm])
    criteria_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a365d')),
    ]))
    elements.append(criteria_table)
    
    elements.append(Spacer(1, 15))
    
    # Reference price
    elements.append(Paragraph(f"<i>Ref {template_data.reference_price} on {underlying}</i>", param_style))
    elements.append(Spacer(1, 10))
    
    # Best strategies section
    elements.append(Paragraph("Best Strategies", section_style))
    
    for i, strat_info in enumerate(template_data.best_strategies, 1):
        strat_text = f"<b>{i} : {strat_info['label']} :</b> {strat_info['description']}"
        elements.append(Paragraph(strat_text, strategy_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def create_pdf_report(
    mixture: tuple,
    template_data: EmailTemplateData,
    comparisons: Optional[List] = None,
) -> Optional[bytes]:
    """
    Create a PDF report with images.
    Single pipeline for PDF generation.
    
    Args:
        template_data: EmailTemplateData with all parameters
        comparisons: List of StrategyComparison (to generate images)
        mixture: Tuple of mixture (for the diagram)
    
    Returns:
        bytes of the PDF for download via Streamlit
    """
    images = []
    
    # Generate images if we have the data
    if comparisons:
        try:
            from myproject.share_result.image_saver import save_all_diagrams
            print("[PDF DEBUG] image_saver imported")
            
            saved_images = save_all_diagrams(comparisons, mixture)
            print(f"[PDF DEBUG] save_all_diagrams returns: {saved_images}")
            
            if saved_images.get('payoff'):
                images.append(saved_images['payoff'])
                print(f"[PDF DEBUG] Payoff added: {saved_images['payoff']}")
            
            if saved_images.get('summary'):
                images.append(saved_images['summary'])
                print(f"[PDF DEBUG] Summary added: {saved_images['summary']}")
                
        except Exception as e:
            print(f"[PDF DEBUG] Error generating images: {e}")
            import traceback
            traceback.print_exc()
    
    return generate_pdf_report(template_data, images)
