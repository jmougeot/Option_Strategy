"""
Email generation module for Options Strategy.
Generates HTML emails with the new template format.
"""
import os
import sys
from typing import List, Optional
from datetime import datetime
from myproject.share_result.utils import (
    EmailTemplateData,
)


def generate_html_email_from_template(
    template_data: EmailTemplateData,
) -> tuple:
    """
    Generate subject and HTML body for a professional email.
    Matches the BGC rates derivatives template format.
    
    Args:
        template_data: EmailTemplateData with all parameters
    
    Returns:
        tuple: (subject, html_body)
    """
    underlying = template_data.underlying or "Options"
    date_str = datetime.now().strftime('%Y-%m-%d')
    subject = f"[Options Strategy] {underlying} - Recommended strategy ({date_str})"
    
    # Build selection criteria section (e.g. "ROLLS THE BEST" and "WITH THE HIGHEST LEVERAGE PnL")
    criteria_items = template_data.selection_criteria or []
    if len(criteria_items) == 1:
        selection_html = f'<p style="font-weight:bold; color:#1a365d; text-transform:uppercase; margin:4px 0;">{criteria_items[0]}</p>'
    elif len(criteria_items) >= 2:
        parts = [f'<p style="font-weight:bold; color:#1a365d; text-transform:uppercase; margin:4px 0;">{criteria_items[0]}</p>']
        for c in criteria_items[1:]:
            parts.append(f'<p style="margin:2px 0;">and</p>')
            parts.append(f'<p style="font-weight:bold; color:#1a365d; text-transform:uppercase; margin:4px 0;">{c}</p>')
        selection_html = "\n".join(parts)
    else:
        selection_html = ""
    
    # Roll description
    roll_html = ""
    if template_data.roll_description:
        roll_html = f'<p style="margin:8px 0;">{template_data.roll_description}</p>'
    
    # Leverage description
    leverage_html = ""
    if template_data.leverage_description:
        connector = "<p style='margin:4px 0;font-weight:bold;'>AND</p>" if template_data.roll_description else ""
        leverage_html = f'{connector}<p style="margin:8px 0;">{template_data.leverage_description}</p>'
    
    # Payoff commentary
    payoff_comment_html = ""
    if template_data.payoff_commentary:
        payoff_comment_html = f'<p style="margin:12px 0; font-style:italic;">{template_data.payoff_commentary}</p>'
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{
    font-family: Aptos, Arial, Helvetica, sans-serif;
    font-size: 12pt;
    line-height: 1.5;
    color: #333;
    max-width: 800px;
    margin: 0;
    padding: 15px;
}}
.intro {{
    font-size: 12pt;
    margin-bottom: 4px;
}}
.section-title {{
    font-weight: bold;
    color: #1a365d;
    margin-top: 8px;
    margin-bottom: 2px;
    display: inline;
}}
.param-value {{
    display: inline;
    margin: 0;
}}
.criteria-block {{
    margin-top: 15px;
    padding: 10px 15px;
    background-color: #f7fafc;
    border-left: 3px solid #1a365d;
}}
.result-block {{
    margin: 15px 0;
}}
.image-container {{
    margin: 15px 0;
    text-align: center;
}}
.image-container img {{
    max-width: 700px;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}
</style>
</head>
<body>

<p class="intro">Pls find below the strategy on {underlying} that</p>

{selection_html}

<div class="result-block">
<p><strong>Result is</strong></p>

<p><strong>{template_data.strategy_result}</strong></p>
<p>{template_data.market_data}</p>

<p style="margin-top:8px;">{template_data.risk_description}</p>

{roll_html}
{leverage_html}
</div>

{payoff_comment_html}

<!-- PAYOFF_DIAGRAM_PLACEHOLDER -->

<!-- TOP10_SUMMARY_PLACEHOLDER -->

<div class="criteria-block">
<p style="font-weight:bold; color:#1a365d; margin-bottom:8px;">CRITERIA:</p>

<p><span class="section-title">FUTURE:</span> <span class="param-value">{underlying}</span></p>
<p><span class="section-title">TARGET:</span> <span class="param-value">{template_data.target_description}</span></p>
<p><span class="section-title">TAIL RISK:</span> <span class="param-value">{template_data.tail_risk_description}</span></p>
<p><span class="section-title">MAX RISK:</span> <span class="param-value">{template_data.max_risk_description}</span></p>
<p><span class="section-title">MAX LEGS:</span> <span class="param-value">{template_data.max_legs} legs ({template_data.max_legs} strikes)</span></p>
<p><span class="section-title">STRIKES SCREENED:</span> <span class="param-value">{template_data.strikes_screened_description}</span></p>
<p><span class="section-title">DELTA:</span> <span class="param-value">{template_data.delta_description}</span></p>
<p><span class="section-title">PREMIUM SPENT MAX:</span> <span class="param-value">{template_data.premium_max_description}</span></p>
</div>

</body>
</html>
"""
    return subject, html


def open_outlook_with_email(
    template_data: EmailTemplateData,
    images: Optional[List[str]] = None,
    to: str = ""
) -> bool:
    """
    Open Outlook with a professional HTML email and embedded images.
    Single pipeline for Outlook email.
    
    Args:
        template_data: EmailTemplateData with all parameters
        images: List of image paths [payoff_diagram, top10_summary]
        to: Recipient email (optional)
    
    Returns:
        True if success, False otherwise
    """
    images = images or []
    
    print("\n" + "="*60)
    print("[Email DEBUG] open_outlook_with_email() called")
    print(f"[Email DEBUG] Number of images received: {len(images)}")
    for i, img in enumerate(images):
        print(f"[Email DEBUG]   Image {i}: {img}")
        if img:
            print(f"[Email DEBUG]   Exists: {os.path.exists(img)}")
        else:
            print(f"[Email DEBUG]   ⚠ Empty path!")
    print("="*60 + "\n")
    
    if sys.platform != "win32":
        print("[Email] open_outlook_with_email is only available on Windows")
        return False
    
    try:
        import pythoncom
        import win32com.client as win32
        
        # Initialize COM for this thread (required with Streamlit)
        pythoncom.CoInitialize()        
        outlook = win32.Dispatch('Outlook.Application')
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        
        # Generate email HTML
        subject, html_content = generate_html_email_from_template(template_data)
        
        if to:
            mail.To = to
        mail.Subject = subject
        
        # Filter valid images
        valid_images = []
        for img_path in images:
            if img_path and os.path.exists(img_path):
                abs_path = os.path.abspath(img_path)
                valid_images.append(abs_path)
                print(f"[Email DEBUG] Valid image: {abs_path}")
            else:
                print(f"[Email DEBUG] Invalid or missing image: {img_path}")
                
        # Replace placeholders with images
        payoff_html = ""
        summary_html = ""
        
        if len(valid_images) > 0:
            payoff_html = '''
<div class="image-container">
<img src="cid:payoff_diagram" alt="Payoff Diagram">
</div>
'''
        if len(valid_images) > 1:
            summary_html = '''
<div class="image-container">
<img src="cid:top10_summary" alt="Top 10 Summary">
</div>
'''

        # Insert images into HTML
        html_content = html_content.replace("<!-- PAYOFF_DIAGRAM_PLACEHOLDER -->", payoff_html)
        html_content = html_content.replace("<!-- TOP10_SUMMARY_PLACEHOLDER -->", summary_html)
        
        # Add images as attachments with CID BEFORE setting HTMLBody
        # (Outlook COM requires attachments to exist before referencing them in HTML)
        PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
        PR_ATTACH_FLAGS = "http://schemas.microsoft.com/mapi/proptag/0x37140003"
        
        cid_names = ["payoff_diagram", "top10_summary"]
        for i, img_path in enumerate(valid_images[:2]):
            cid = cid_names[i] if i < len(cid_names) else f"image{i}"
            try:
                attachment = mail.Attachments.Add(img_path)
                print(f"[Email DEBUG] Attachment added: {img_path}")
                
                attachment.PropertyAccessor.SetProperty(PR_ATTACH_CONTENT_ID, cid)
                # Mark as inline attachment (hidden from attachment list)
                attachment.PropertyAccessor.SetProperty(PR_ATTACH_FLAGS, 4)
                print(f"[Email DEBUG] CID set: {cid}")
                
            except Exception as att_err:
                print(f"[Email DEBUG] Error adding attachment: {att_err}")
        
        # Set HTMLBody AFTER adding attachments so CID references resolve
        mail.HTMLBody = html_content
        print("[Email DEBUG] HTMLBody set")
        
        mail.Display(False)
        
        pythoncom.CoUninitialize()
        
        return True
        
    except ImportError as ie:
        print(f"[Email] pywin32 module not installed: {ie}")
        print("[Email] Install with: pip install pywin32")
        return False
    except Exception as e:
        print(f"[Email] Outlook error: {e}")
        import traceback
        traceback.print_exc()
        return False

