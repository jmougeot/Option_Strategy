"""
Email utilities module for Options Strategy.
Provides clean pipelines for Outlook email and PDF generation.
"""
from typing import Dict, Any, List, Optional

# Re-export StrategyEmailData and EmailTemplateData from utils
from myproject.share_result.utils import StrategyEmailData, EmailTemplateData

# Import the single pipeline functions
from myproject.share_result.generate_email import (
    open_outlook_with_email,
)



def create_email_with_images(
    template_data: EmailTemplateData,
    comparisons: Optional[List] = None,
    mixture: Optional[tuple] = None,
) -> bool:
    """
    Create an Outlook email with embedded images.
    Single pipeline for Outlook email.
    
    Args:
        template_data: EmailTemplateData with all parameters
        comparisons: List of StrategyComparison (to generate images)
        mixture: Tuple of mixture (for the diagram)
    
    Returns:
        True if email was opened successfully
    """
    images = []
    
    # Generate images if we have the data
    if comparisons:
        try:
            from myproject.app.image_saver import save_all_diagrams
            print("[Email DEBUG] image_saver imported")
            
            saved_images = save_all_diagrams(comparisons, mixture)
            print(f"[Email DEBUG] save_all_diagrams returns: {saved_images}")
            
            if saved_images.get('payoff'):
                images.append(saved_images['payoff'])
                print(f"[Email DEBUG] Payoff added: {saved_images['payoff']}")
            
            if saved_images.get('summary'):
                images.append(saved_images['summary'])
                print(f"[Email DEBUG] Summary added: {saved_images['summary']}")
                
        except Exception as e:
            print(f"[Email DEBUG] Error generating images: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[Email DEBUG] No comparisons provided - no images to generate")
    
    print(f"[Email DEBUG] Final images list: {images}")
    
    # Open Outlook with the template and images
    success = open_outlook_with_email(
        template_data=template_data,
        images=images
    )
    
    if not success:
        print("[Email] ❌ Could not open Outlook.")
        if images:
            print("[Email] Generated images:")
            for img in images:
                print(f"   - {img}")
    
    return success
