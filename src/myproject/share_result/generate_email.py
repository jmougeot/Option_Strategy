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
    Based on the new BGC template format.
    
    Args:
        template_data: EmailTemplateData with all parameters
    
    Returns:
        tuple: (subject, html_body)
    """
    underlying = template_data.underlying or "Options"
    date_str = datetime.now().strftime('%Y-%m-%d')
    subject = f"[Options Strategy] {underlying} - Recommended strategies ({date_str})"
    
    # Build the strategies results section
    best_strategies_html = ""
    for i, strat_info in enumerate(template_data.best_strategies, 1):
        best_strategies_html += f"""<p><strong>{i} : {strat_info['label']} :</strong> {strat_info['description']}</p>
"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #333;
    max-width: 800px;
    margin: 0;
    padding: 15px;
}}
.intro {{
    font-size: 10pt;
    margin-bottom: 10px;
}}
.section-title {{
    font-weight: bold;
    color: #1a365d;
    margin-top: 12px;
    margin-bottom: 3px;
}}
.param-line {{
    margin: 3px 0;
    padding-left: 0;
}}
.strategy-result {{
    margin: 8px 0;
    padding-left: 0;
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
.signature {{
    margin-top: 20px;
    color: #4a5568;
}}
</style>
</head>
<body>

<p class="intro">Hi team,</p>

<p class="intro">You will find below the strategies meeting the below criteria :</p>

<p class="section-title">TARGET:</p>
<p class="param-line">{template_data.target_description}</p>

<p class="section-title">TAIL RISK:</p>
<p class="param-line">{template_data.tail_risk_description}</p>

<p class="section-title">MAX RISK:</p>
<p class="param-line">{template_data.max_risk_description}</p>

<p class="section-title">MAX LEGS:</p>
<p class="param-line">{template_data.max_legs} legs ({template_data.max_legs} strikes)</p>

<p class="section-title">STRIKES SCREENED:</p>
<p class="param-line">{template_data.strikes_screened_description}</p>

<p class="section-title">DELTA:</p>
<p class="param-line">{template_data.delta_description}</p>

<p class="section-title">PREMIUM SPENT MAX:</p>
<p class="param-line">{template_data.premium_max_description}</p>

<p class="section-title">MAX LOSS:</p>
<p class="param-line">{template_data.max_loss_description}</p>

<p class="section-title">WEIGHTING:</p>
<p class="param-line">{template_data.weighting_description}</p>

<p style="margin-top: 15px;"><em>Ref {template_data.reference_price} on {underlying},</em></p>

<div style="margin-top: 15px;">
{best_strategies_html}
</div>

<!-- PAYOFF_DIAGRAM_PLACEHOLDER -->

<!-- TOP10_SUMMARY_PLACEHOLDER -->

<p class="signature">
Best regards,<br>
<strong>BGC's team of rates derivatives</strong>
</p>

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
        print("[Email DEBUG] COM initialized")
        
        outlook = win32.Dispatch('Outlook.Application')
        print("[Email DEBUG] Outlook.Application created")
        
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        print("[Email DEBUG] Mail item created")
        
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
                print(f"[Email DEBUG] ✓ Valid image: {abs_path}")
            else:
                print(f"[Email DEBUG] ✗ Invalid or missing image: {img_path}")
                
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
        
        # Set HTMLBody
        mail.HTMLBody = html_content
        print("[Email DEBUG] HTMLBody set")
        
        # Add images as attachments with CID
        PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
        
        cid_names = ["payoff_diagram", "top10_summary"]
        for i, img_path in enumerate(valid_images[:2]):
            cid = cid_names[i] if i < len(cid_names) else f"image{i}"
            try:
                attachment = mail.Attachments.Add(img_path)
                print(f"[Email DEBUG] Attachment added: {img_path}")
                
                attachment.PropertyAccessor.SetProperty(PR_ATTACH_CONTENT_ID, cid)
                print(f"[Email DEBUG] CID set: {cid}")
                
            except Exception as att_err:
                print(f"[Email DEBUG] ✗ Error adding attachment: {att_err}")
        
        # Display the email (non-modal)
        print("[Email DEBUG] Calling mail.Display(False)...")
        mail.Display(False)
        print("[Email DEBUG] ✓ Email displayed successfully")
        
        # Release COM
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

