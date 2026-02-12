"""
Help Tab - Detailed explanation of scoring criteria, filters and parameters
"""

import streamlit as st


def run():
    """Displays the help tab with complete explanations."""
    
    st.header("Complete Guide")
    
    st.markdown("""
    This guide explains all parameters, filters and scoring criteria used in the application.
    Use the menu below to navigate to the desired section.
    """)
    
    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    
    st.markdown("""
    **Table of Contents:**
    1. [Market Scenarios](#market-scenarios)
    2. [Search Parameters](#search-parameters)
    3. [Strategy Filters](#strategy-filters)
    4. [Scoring Criteria](#scoring-criteria)
    5. [Advanced Criteria (Greeks)](#advanced-criteria)
    6. [Scoring System](#scoring-system)
    """)
    
    st.markdown("---")
    
    # =========================================================================
    # MARKET SCENARIOS
    # =========================================================================
    
    st.subheader("🎯 Market Scenarios", anchor="market-scenarios")
    
    st.markdown("""
    Scenarios define your expectations for the underlying price at expiration.
    They are modeled using a **Gaussian mixture** (blend of normal distributions).
    """)
    
    with st.expander("📊 Target Price", expanded=True):
        st.markdown("""
        **Definition:** The price you expect the underlying to reach for this scenario.
        
        **Example:** 
        - Target = 98.50 means you anticipate a price of 98.50 at expiration
        
        **Usage:**
        - This is the center of the Gaussian distribution for this scenario
        - Multiple scenarios allow modeling different possibilities (up, down, range-bound)
        """)
    
    with st.expander("📈 Uncertainty (σ)"):
        st.markdown("""
        **Definition:** The standard deviation of the Gaussian distribution around the target price.
        
        **Formula:** The probability that price is between $\\mu - \\sigma$ and $\\mu + \\sigma$ is ~68%
        
        **Interpretation:**
        - **Small σ (0.05)**: You are very confident in your prediction
        - **Large σ (0.20)**: High uncertainty, price can vary significantly
        
        **Asymmetric Mode:**
        - **σ left**: Downside uncertainty
        - **σ right**: Upside uncertainty
        - Allows modeling a bias (e.g., more downside risk than upside)
        """)
    
    with st.expander("⚖️ Probability (Weight)"):
        st.markdown("""
        **Definition:** The relative weight of this scenario compared to others.
        
        **Normalization:** Weights are automatically normalized so their sum = 100%
        
        **Example with 2 scenarios:**
        - Scenario 1: Target=98.0, Weight=60
        - Scenario 2: Target=99.0, Weight=40
        - → 60% chance for scenario 1, 40% for scenario 2
        
        **Tip:** Use probabilities to reflect your conviction in each scenario.
        """)
    
    with st.expander("🔀 Gaussian Mixture - How it works"):
        st.markdown("""
        **Density formula:**
        $$f(x) = \\sum_{i=1}^{n} w_i \\cdot \\mathcal{N}(x | \\mu_i, \\sigma_i)$$
        
        Where:
        - $w_i$ = Normalized weight of scenario i
        - $\\mu_i$ = Target price of scenario i
        - $\\sigma_i$ = Uncertainty of scenario i
        - $\\mathcal{N}$ = Normal distribution
        
        **Advantages:**
        - Models **multimodal** distributions (multiple possible peaks)
        - Naturally captures **fat tails**
        - Allows **asymmetric** distributions
        
        **Visualization:** The P&L diagram shows the probability curve in the background.
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # SEARCH PARAMETERS
    # =========================================================================
    
    st.subheader("⚙️ Search Parameters", anchor="search-parameters")
    
    with st.expander("🏷️ Underlying"):
        st.markdown("""
        **Definition:** The Bloomberg code of the underlying.
        
        **Common examples:**
        - **ER** = EURIBOR 3 months
        - **ED** = Eurodollar
        - **TY** = US Treasury 10Y
        
        **Full format:** Underlying + Month + Year (e.g., ERH6 = EURIBOR March 2026)
        """)
    
    with st.expander("📅 Years & Months"):
        st.markdown("""
        **Years:**
        - Format: 1 digit (6 = 2026, 7 = 2027)
        - Multiple: separate with comma (6, 7)
        
        **Months (Expiration):**
        - **H** = March
        - **M** = June
        - **U** = September
        - **Z** = December
        
        **Example:** Months=H, Years=6 → Options expiring in March 2026
        """)
    
    with st.expander("💰 Price Range (Min/Max/Step)"):
        st.markdown("""
        **Min Price / Max Price:**
        - Defines the range of strikes to consider
        - Options with strikes outside this range are ignored
        
        **Price Step:**
        - The increment between strikes (tick size)
        - E.g., 0.0625 for EURIBOR (1/16th of a point)
        
        **Impact:** Wider range = more options = more combinations = longer computation time
        """)
    
    with st.expander("🦵 Max Legs"):
        st.markdown("""
        **Definition:** The maximum number of options in a strategy.
        
        **Examples by number of legs:**
        - **1 leg**: Simple call or put
        - **2 legs**: Spreads (bull call, bear put), straddles, strangles
        - **3 legs**: Butterflies, ladders
        - **4 legs**: Condors, iron butterflies
        - **5+ legs**: Custom complex strategies
        
        **Performance:** More legs = exponentially more combinations
        - 2 legs: ~N² combinations
        - 4 legs: ~N⁴ combinations
        """)
    
    with st.expander("🔄 Roll Months"):
        st.markdown("""
        **Definition:** The expiries to calculate roll into.
        
        **Format:** M + Y (e.g., Z5, H6)
        - Z5 = December 2025
        - H6 = March 2026
        
        **Multiple:** Separate with comma (Z5, H6, M6)
        
        **Usage:** 
        - Compares current strategy price vs same strategy on a future expiry
        - Useful for evaluating the cost of maintaining a position over time
        """)
    
    with st.expander("📝 Raw Code Mode"):
        st.markdown("""
        **Definition:** Advanced mode to directly specify Bloomberg codes.
        
        **Format:** Codes separated by comma
        - E.g., RXWF26C2, RXWF26P2
        
        **Usage:** 
        - To access non-standard options
        - For underlyings with special naming conventions
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # FILTERS
    # =========================================================================
    
    st.subheader("🔍 Strategy Filters", anchor="strategy-filters")
    
    st.markdown("""
    Filters eliminate strategies that don't match your criteria **before** scoring.
    They reduce the search space and speed up computation.
    """)
    
    with st.expander("📉 Max Loss Left / Right", expanded=True):
        st.markdown("""
        **Definition:** The maximum loss allowed in each direction.
        
        **Max Loss Left:** Max loss if price drops (below Limit Left)
        **Max Loss Right:** Max loss if price rises (above Limit Right)
        
        **Example:**
        - Max Loss Left = 0.10, Limit Left = 98.50
        - → Strategy cannot lose more than 0.10 if price < 98.50
        
        **"Unlimited Loss" Checkbox:**
        - Disables this filter (allows unlimited losses)
        - ⚠️ Be careful with naked short strategies!
        """)
    
    with st.expander("🎯 Limit Left / Right"):
        st.markdown("""
        **Definition:** The thresholds where Max Loss filters apply.
        
        **Limit Left:** Price below which Max Loss Left applies
        **Limit Right:** Price above which Max Loss Right applies
        
        **Logic:**
        - If price < Limit Left → verify loss ≤ Max Loss Left
        - If price > Limit Right → verify loss ≤ Max Loss Right
        
        **Tip:** Align these limits with your extreme scenarios.
        """)
    
    with st.expander("💵 Max Premium"):
        st.markdown("""
        **Definition:** The maximum cost (absolute value) to put on the strategy.
        
        **Interpretation:**
        - Filters out strategies that are too expensive
        - Applies to absolute value (covers both debit and credit)
        
        **Example:** Max Premium = 0.05 → rejects strategies costing > 0.05
        """)
    
    with st.expander("💰 Min Price for Short"):
        st.markdown("""
        **Definition:** The minimum price an option must be worth to be sold.
        
        **Usage:**
        - Avoids selling worthless options (illiquid)
        - Filters deep OTM options with negligible premium
        
        **Example:** Min = 0.005 → don't sell options worth less than 0.005
        """)
    
    with st.expander("📊 PUT: Short-Long / CALL: Short-Long (Net Exposure)"):
        st.markdown("""
        **Definition:** The difference between options sold and bought by type.
        
        **PUT: Short-Long:**
        - = 0: Equal puts sold and bought (closed position on the left)
        - > 0: More puts sold than bought (bearish exposure)
        - < 0: More puts bought than sold (downside protection)
        
        **CALL: Short-Long:**
        - = 0: Equal calls sold and bought (closed position on the right)
        - > 0: More calls sold than bought (bullish exposure)
        - < 0: More calls bought than sold (upside protection)
        
        **Example:** 
        - PUT=0, CALL=0 → Perfectly closed strategies (condors, butterflies)
        - PUT=1, CALL=0 → Can sell 1 more put than bought
        """)
    
    with st.expander("Δ Delta Min / Max"):
        st.markdown("""
        **Definition:** Constraints on the strategy's total delta.
        
        **Typical range:** -1.0 to +1.0 (or -100% to +100%)
        
        **Examples:**
        - Delta Min = -0.10, Delta Max = +0.10 → Near-neutral strategies
        - Delta Min = 0.20, Delta Max = 0.50 → Moderate bullish bias
        
        **Usage:** Controls the directional bias of the strategy.
        """)
    
    with st.expander("📋 Select Strategy Type"):
        st.markdown("""
        **Definition:** Filter to include only certain predefined strategy types.
        
        **Available types:**
        - **Put Condor**: 4 puts forming a condor
        - **Call Condor**: 4 calls forming a condor
        - **Put Ladder**: 3 puts (e.g., 1 long, 2 shorts)
        - **Call Ladder**: 3 calls (e.g., 1 long, 2 shorts)
        - **Put Fly**: 3 puts forming a butterfly
        - **Call Fly**: 3 calls forming a butterfly
        
        **Note:** This filter uses pattern recognition on the strategy structure.
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # MAIN CRITERIA
    # =========================================================================
    
    st.subheader("🎯 Scoring Criteria", anchor="scoring-criteria")
    
    # Expected Gain (Average P&L)
    with st.expander("📈 Expected Gain at Expiry (Average P&L)", expanded=True):
        st.markdown("""
        **Definition:** The expected average profit of the strategy at expiration, weighted by the 
        probability distribution of underlying prices (Gaussian mixture).
        
        **Formula:**
        $$PM = \\int_{-\\infty}^{+\\infty} P\\&L(S) \\cdot f(S) \\, dS$$
        
        Where:
        - $P\\&L(S)$ = Profit/Loss if underlying ends at $S$
        - $f(S)$ = Probability density (Gaussian mixture defined by your scenarios)
        
        **Interpretation:**
        - **PM > 0**: Strategy is profitable on average according to your expectations
        - **PM < 0**: Strategy loses money on average
        - **Higher = Better**
        
        **Example:** If PM = 0.50, it means for 1€ notional, you gain 0.50€ on average.
        """)
    
    # Leverage of Expected Gain
    with st.expander("⚡ Leverage of Expected Gain"):
        st.markdown("""
        **Definition:** The ratio between expected average profit and net premium paid/received.
        Measures capital efficiency.
        
        **Formula:**
        $$Leverage = \\frac{PM}{|Premium|}$$
        
        **Interpretation:**
        - **Leverage = 2**: You earn 2€ for every 1€ of premium paid
        - **High leverage**: Great capital efficiency
        - **Higher = Better**
        
        **Warning:** Very high leverage may indicate a risky strategy with low probability of success.
        """)
    
    # Roll
    with st.expander("🔄 Roll (first selected expiry)"):
        st.markdown("""
        **Definition:** The price difference between the current option and the same option 
        on the first roll expiry selected in the parameters.
        
        **Formula:**
        $$Roll = Price_{roll[0]} - Price_{current}$$
        
        **Interpretation:**
        - **Roll > 0**: Option is more expensive on the selected roll expiry (contango)
        - **Roll < 0**: Option is cheaper on the next expiry (backwardation)
        - For a **long** position, positive roll is favorable (time value increases)
        - **Higher = Better** (for long positions)
        
        **Usage:** Useful for evaluating the cost of maintaining a position over time.
        """)
    
    # Tail Risk Penalty (Max Loss)
    with st.expander("⚠️ Tail Risk Penalty"):
        st.markdown("""
        **Definition:** Measures the risk of extreme losses in the distribution tails.
        Penalizes strategies that lose heavily in unlikely but possible scenarios.
        
        **Formula:**
        $$Tail\\ Penalty = \\int max(-P\\&L(S), 0)^2 \\cdot f(S) \\, dS$$
        
        **Interpretation:**
        - **Tail Penalty = 0**: No loss risk in extremes
        - **High Tail Penalty**: Significant losses possible in extreme scenarios
        - **Lower = Better**
        
        **Example:** A naked put sale will have a very high Tail Penalty because losses 
        can be unlimited if the market crashes.
        """)
    
    # Average Intra-Life P&L
    with st.expander("📊 Avg Intra-Life P&L"):
        st.markdown("""
        **Definition:** The average profit/loss of the strategy at intermediate dates 
        before expiration, calculated using the Bachelier model.
        
        **Calculation:**
        1. Divide the period into 5 dates: 20%, 40%, 60%, 80%, 100% of duration
        2. For each date, calculate option price with Bachelier
        3. Average P&L across all these dates
        
        **Interpretation:**
        - **Avg Intra-Life > 0**: Strategy is profitable even before expiration
        - **Avg Intra-Life < 0**: Strategy may lose money if exiting before expiration
        - **Higher = Better**
        
        **Usage:** Important if you plan to potentially close the position before expiry.
        """)
    
    # Premium
    with st.expander("💰 Premium (Net Premium)"):
        st.markdown("""
        **Definition:** The net premium paid or received to set up the strategy.
        
        **Formula:**
        $$Premium = \\sum_{i} sign_i \\times premium_i$$
        
        Where:
        - $sign_i$ = +1 for buy, -1 for sell
        - $premium_i$ = Price of option i
        
        **Interpretation:**
        - **Premium > 0**: You pay to set up the strategy (debit)
        - **Premium < 0**: You receive money (credit)
        - **Closer to 0 = Better** (if weight is enabled)
        
        **Strategies:**
        - **Zero-cost** strategies: Iron condors, balanced butterflies
        - **Credit** strategies: Option selling, credit spreads
        - **Debit** strategies: Option buying, debit spreads
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # SCORING SYSTEM
    # =========================================================================
    
    st.subheader("⚙️ How Scoring Works", anchor="scoring-system")
    
    st.markdown("""
    ### Weighted Geometric Mean
    
    The final score of each strategy is calculated using a **weighted geometric mean** of normalized scores:
    
    $$Score = \\exp\\left(\\sum_{i} w_i \\cdot \\log(\\epsilon + s_i)\\right)$$
    
    Where:
    - $w_i$ = Weight of criterion i (normalized so $\\sum w_i = 1$)
    - $s_i$ = Normalized score of criterion i (between 0 and 1)
    - $\\epsilon$ = 10⁻⁶ (to avoid log(0))
    
    ### Advantages of this approach:
    1. **Balance**: A very low score on an important criterion heavily penalizes the overall score
    2. **Flexibility**: Weights allow customizing the importance of each criterion
    3. **Normalization**: All criteria are on the same scale [0, 1]
    
    ### Criterion normalization:
    - **MAX**: Divide by maximum → used for criteria where closer to 0 = better
    - **MIN_MAX**: $(x - min) / (max - min)$ → used for criteria with a range of values
    """)
    
    st.markdown("---")
    
    # =========================================================================
    # USAGE TIPS
    # =========================================================================
    
    st.subheader("💡 Usage Tips")
    
    st.markdown("""
    ### Suggested strategy profiles:
    
    | Profile | Criteria to prioritize |
    |---------|----------------------|
    | **Conservative** | Low Max Loss, Low Tail Penalty, Positive PM |
    | **Aggressive** | High Leverage, High PM (accepts more risk) |
    | **Neutral** | Delta Neutral, Gamma Low, Vega Low |
    | **Carry Trade** | High Roll, Positive Theta |
    | **Short-term** | High Avg Intra-Life P&L |
    
    ### Best practices:
    1. **Start simple**: Enable 2-3 criteria maximum at first
    2. **PM is essential**: Always keep a weight on Expected Gain
    3. **Balance risk/reward**: Combine PM with Max Loss or Tail Penalty
    4. **Verify visually**: Use the P&L diagram to validate strategies
    """)
