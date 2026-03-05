"""
Email generation module for Options Strategy.
Generates HTML emails with the new template format.
"""
import os
import sys
from typing import List, Optional
from datetime import datetime
from share_result.utils import (
    EmailTemplateData,
)


def generate_html_email_from_template(
    template_data: EmailTemplateData,
    fields: Optional[dict] = None,
    strat_data: Optional[List[dict]] = None,
) -> tuple:
    """
    Generate subject and HTML body following the exact BGC trade-recommendation template.
    """
    f = fields or {}
    sd = strat_data or []

    underlying      = f.get("expiry_code") or template_data.underlying or "Options"
    client_name     = f.get("client_name",     "XXX")
    target          = f.get("target",          "XXX")
    target_date     = f.get("target_date",     "XXX")
    und_price       = f.get("underlying_price","XXX")
    uncert_l        = f.get("uncert_left",     "XXX")
    uncert_r        = f.get("uncert_right",    "XXX")
    tail_l          = f.get("tail_left",       "XXX")
    tail_r          = f.get("tail_right",      "XXX")
    limit_l         = f.get("limit_left",      "XXX")
    limit_r         = f.get("limit_right",     "XXX")
    open_risk       = f.get("open_risk",       "XXX")
    max_legs        = f.get("max_legs",        str(template_data.max_legs))
    price_min       = f.get("price_min",       "XXX")
    price_max       = f.get("price_max",       "XXX")
    price_step      = f.get("price_step",      "XXX")
    min_short       = f.get("min_short",       "XXX")
    delta_min       = f.get("delta_min",       "XXX")
    delta_max       = f.get("delta_max",       "XXX")
    signature       = f.get("signature",       "XXX")
    screened        = f.get("nb_screened",  0)


    date_str = datetime.now().strftime("%Y-%m-%d")
    subject  = f"[Options Strategy] {underlying} — Trade Recommendation ({date_str})"

    summary_rows = ""
    for s in sd:
        summary_rows += f'<p style="margin:6px 0;">{s["idx"]} : {s["line"]}</p>\n'

    # ── detail blocks ──────────────────────────────────────────────────────────
    detail_blocks = ""
    for s in sd:
        i       = s["idx"] - 1      # 0-based index for CID
        comment = s.get("commentary") or "XXXX"
        prem    = s.get("premium",       0.0)
        avg_pnl = s.get("avg_pnl",       0.0)
        max_pft = s.get("max_profit",    0.0)
        max_at  = s.get("max_profit_at", "XXX")
        lvg     = s.get("leverage",      0.0)
        be      = s.get("breakeven",     "XXX")

        detail_blocks += f"""
<p style="margin:12px 0; color: #991b1b;"><strong>{s['idx']} : {s['line']}</strong></p>

<p style="margin:8px 0;">The model, and we, chose this strategy because {comment}</p>

<p style="margin:14px 0 4px;"><strong>Statistics&nbsp;:</strong></p>
<p style="margin:3px 0;">&bull;&nbsp;Leverage&nbsp;: {lvg:.2f} &mdash; pay {prem:.4f} to make {avg_pnl:.4f} net on average (using the gaussian model)</p>
<p style="margin:3px 0;">&bull;&nbsp;Max Profit&nbsp;: {max_pft:.4f} (premium considered) at {max_at}</p>
<p style="margin:3px 0;">&bull;&nbsp;Breakeven profit&nbsp;: from {be}</p>


<p style="margin:12px 0;">See below the top strategies chose by the model (Strategy {s['idx']} Selected)&nbsp;:</p>

<!-- PAYOFF_{i}_PLACEHOLDER -->
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{
    font-family: Aptos, Arial, Helvetica, sans-serif;
    font-size: 12pt;
    line-height: 1.5;
    color: #222;
    background-color: #ffffff;
    max-width: 820px;
    margin: 0;
    padding: 20px;
}}
</style>
</head>
<body>

<p>Dear {client_name},</p>

<p>&nbsp;</p>

<p>As requested, here are the best trades in our opinion in <strong>{underlying}</strong></p>

<p>Helped by the option model we&#8217;re building (M2O, Macro to Options &#128521;)</p>

<p>Trades on <strong>{underlying}</strong> to Target <strong>{target}</strong> by the end of <strong>{target_date}</strong></p>

<p>&nbsp;</p>

<p style="color:#991b1b;"><strong>Risk Criteria&nbsp;:</strong></p>

<p>&bull;&nbsp;<strong>Underlying</strong> : {und_price}</p>
<p>&bull;&nbsp;<strong>Target</strong> : {target} with {uncert_l}&nbsp;bp uncertainty on the left and {uncert_r}&nbsp;bp uncertainty on the right</p>
<p>&bull;&nbsp;<strong>Tail Risk</strong> : {tail_l} tick loss on the downside / {tail_r} tick loss on the upside, starting from {limit_l} / {limit_r}</p>
<p>&bull;&nbsp;<strong>Open Risk</strong> : 1x2 {open_risk}</p>
<p>&bull;&nbsp;<strong>Maximum legs</strong> : {max_legs}</p>
<p>&bull;&nbsp;<strong>Strikes Screened</strong> : Looking at all options between {price_min} and {price_max}. Every {price_step} ticks. Cannot short any option for less than {min_short} tick.</p>
<p>&bull;&nbsp;<strong>Delta</strong> : From {delta_min} to {delta_max}</p>
<p>&bull;&nbsp;<strong>Expiry</strong> : {underlying}</p>
<p style="margin:3px 0;">&bull;&nbsp;Strategies Screened&nbsp;: {screened}</p>

<p>&nbsp;</p>

<p style="color:#991b1b;"><strong>Best trades to fit this curve according to M2O are&nbsp;:</strong></p>

{summary_rows}

<p>&nbsp;</p>

<p><strong>DETAILS BELOW&nbsp;:</strong></p>

{detail_blocks}

<p>&nbsp;</p>

<p>Happy to discuss&nbsp;!</p>

<p>&nbsp;</p>

<p>{signature}</p>

<p>&nbsp;</p>

<p>Best Regards,</p>

</body>
</html>
"""
    return subject, html


def open_outlook_with_email(
    template_data: EmailTemplateData,
    images: Optional[List[str]] = None,
    payoff_images: Optional[List[str]] = None,
    fields: Optional[dict] = None,
    strat_data: Optional[List[dict]] = None,
    to: str = ""
) -> bool:
    """
    Open Outlook with a professional HTML email and embedded images.

    Args:
        template_data: EmailTemplateData with all parameters
        images: Legacy [payoff, summary] pair (used when payoff_images is None)
        payoff_images: One PNG path per selected strategy (takes priority)
        to: Recipient email (optional)

    Returns:
        True if success, False otherwise
    """
    images = images or []
    payoff_images = payoff_images or []

    # payoff_images takes priority; fall back to legacy images list
    all_payoff_paths: List[str] = payoff_images if payoff_images else images[:1]
    summary_path: Optional[str] = None if payoff_images else (images[1] if len(images) > 1 else None)

    try:
        import pythoncom
        import win32com.client as win32

        pythoncom.CoInitialize()
        outlook = win32.Dispatch('Outlook.Application')
        mail = outlook.CreateItem(0)

        subject, html_content = generate_html_email_from_template(template_data, fields=fields, strat_data=strat_data)

        if to:
            mail.To = to
        mail.Subject = subject

        # Validate paths
        valid_payoffs = [
            os.path.abspath(p) for p in all_payoff_paths
            if p and os.path.exists(p)
        ]
        valid_summary = os.path.abspath(summary_path) \
            if summary_path and os.path.exists(summary_path) else None

        # Replace each per-strategy placeholder <!-- PAYOFF_i_PLACEHOLDER --> with its <img>
        for i, _ in enumerate(valid_payoffs):
            cid = f"payoff_{i}"
            img_tag = f'<div style="margin:12px 0;"><img src="cid:{cid}" alt="Payoff Diagram {i+1}" width="1100" style="display:block;"></div>'
            html_content = html_content.replace(f"<!-- PAYOFF_{i}_PLACEHOLDER -->", img_tag)

        if valid_summary:
            summary_html = '<div style="margin:12px 0;"><img src="cid:top10_summary" alt="Top 10 Summary" width="1100" style="display:block;"></div>'
            html_content = html_content.replace("<!-- TOP10_SUMMARY_PLACEHOLDER -->", summary_html)

        # HTMLBody MUST be set before adding inline CID attachments
        mail.HTMLBody = html_content

        PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"

        # Attach each payoff image with its own CID
        for i, img_path in enumerate(valid_payoffs):
            cid = f"payoff_{i}"
            try:
                att = mail.Attachments.Add(img_path)
                att.PropertyAccessor.SetProperty(PR_ATTACH_CONTENT_ID, cid)
            except Exception as att_err:
                print(f"[Email DEBUG] Error attaching {img_path}: {att_err}")

        if valid_summary:
            try:
                att = mail.Attachments.Add(valid_summary)
                att.PropertyAccessor.SetProperty(PR_ATTACH_CONTENT_ID, "top10_summary")
            except Exception as att_err:
                print(f"[Email DEBUG] Error attaching summary: {att_err}")

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

