from random import random

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from math import sqrt

from rich.console import Console
from rich.table import Table
from rich.theme import Theme
from rich import print

custom_theme = Theme({
    "info": "dim cyan",
    "title": "green",
    "danger": "bold red"
})

console = Console(theme=custom_theme)

from scripts.loggers.amm_price_impact_logger import AmmPriceImpactLogger, AmmPriceImpactEntry, AmmBruteForceLogger, AMMBruteForceEntry

sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = 15, 30

"""
  Simulation around the ideal partial liquidation behavior

  The following sim aims to show:
  - A CDP of 50 - 99% size needing to get liquidated
  - In a scenario of 0 AMM Liquidity (Liquidator needs to take on the debt)
  - With TCR at 150% (slightly above Recovery Mode)

  Minimal Liquidation Size (MLS)
  Partial Liquidations from MLS to 100%
  Modelling of fees and profit profile based on the value
"""

def price_given_in(amount_in, reserve_in, reserve_out):
  out = amount_out_given_in(amount_in, reserve_in, reserve_out)
  return amount_in / out

def amount_out_given_in(amount_in, reserve_in, reserve_out):
  amount_out = reserve_out * amount_in / (reserve_in + amount_in)
  return amount_out


"""
  Derived by the above
"""
def amount_in_give_out(amount_out, reserve_in, reserve_out):
  amount_in = reserve_in * amount_out / (reserve_out - amount_out)
  return amount_in

def max_in_before_price_limit(price_limit, reserve_in, reserve_out):
  return reserve_out * price_limit - reserve_in

def max_in_before_price_limit_sqrt(price_limit, reserve_in, reserve_out):
  return sqrt(reserve_out * reserve_in * price_limit) - reserve_in



MAX_LTV = 8_500 ## 85% / 117.647058824% CR

## TODO: Change to correct value
MINT_LTV = 7_500 ## 133.333333333% CR
MIN_LTV = 1_000 ## Minimum Leverage else sim is boring
MAX_BPS = 10_000
MAX_LIQUIDITY = 9_500 #95%

MIN_ICR = 1 / 8_500 * MAX_BPS * 100

## TODO: Change back to 13
START_PRICE = 1 ## e.g. 13 eth to btc


AMT_ETH = 1000e18

# 70 BPS (roughly greater than fees)
## We set at 0 for now
MIN_PROFIT = 0
MAX_PROFIT = MAX_BPS - MAX_LTV


def main():
  ## TODO: RANGE FOR INSOLVENCY

  ## 1k ETH as base value
  TOTAL_ETH_COLL = 1000e18

  ## MAX MAX_LTV AT MAX_LTV means we're at the edge of Recovery Mode
  ## TODO: Prob need to change

  ## Add 10% just in case
  AVG_LTV = random() * MINT_LTV + MIN_LTV
  ## Take it back if too much
  if(AVG_LTV > MINT_LTV):
    AVG_LTV -= MIN_LTV
  
  price_ratio = START_PRICE

  ## Divide by 13 as it's 13 ETH per BTC
  TOTAL_BTC_DEBT = TOTAL_ETH_COLL / price_ratio * AVG_LTV / MAX_BPS

  console.print("=== Initial State ===", style="title")
  print("START_PRICE", START_PRICE)
  print("TOTAL_ETH_COLL", TOTAL_ETH_COLL/1e18)
  print("TOTAL_BTC_DEBT", TOTAL_BTC_DEBT/1e18)
  print("")

  ## Between 50 and 99.999999999%
  liquidation_percent = random() * 5_000 + 5_000
  print("Assuming CDP Whale is", liquidation_percent / MAX_BPS * 100, "percent of all debt")
  
  console.print("\n============================", style="title")
  console.print("===== Full Liquidation =====", style="title")
  console.print("============================\n", style="title")
  console.print("\tWe will liquidate this whale entirely", style="info")
  console.print("\tDue to the lack of liquidity, the liquidator will open a position with their own ETH stack", style="info")
  console.print("\tSo the outstanding debt of the system will remain the same\n", style="info")

#   liquidation_collateral_amount = TOTAL_ETH_COLL * liquidation_percent / MAX_BPS
  
  ## TODO: Add Discrete Liquidation amounts
  ## ASSUME 1% Insolvency
  ## TODO: Convert 100 as param to make sim generalizeable
  INSOLVENT_LTV = MAX_LTV + 100 ## 1% over Max

#   liquidation_debt_amount = liquidation_collateral_amount / price_ratio * (INSOLVENT_LTV) / MAX_BPS

  liquidation_debt_amount = TOTAL_BTC_DEBT * (liquidation_percent / MAX_BPS)
  liquidation_collateral_amount = liquidation_debt_amount * price_ratio * MAX_BPS / INSOLVENT_LTV

  console.print("=== Pre-liquidation calcs ===",style="title")
  print("We need to liquidate ", liquidation_debt_amount / 1e18, " (liquidation_debt_amount) eBTC to clear the whale")
  print("This returns", liquidation_collateral_amount / 1e18, " (liquidation_collateral_amount) ETH as collateral")

  ## SANITY CHECKS
  ## RATIO BETWEEN DEBT AND COLL IS GREATER MAX
  ICR = liquidation_collateral_amount / price_ratio / liquidation_debt_amount * 100
  print("ICR (current CR of whale CDP):", ICR)
  print("MCR (the value we want to be above):", MIN_ICR)
  

  assert ICR < MIN_ICR

  ## WHILE CDP IS INSOLVENT, SYSTEM IS FINE
  INITIAL_SYSTEM_CR = TOTAL_ETH_COLL / price_ratio / TOTAL_BTC_DEBT * 100
  print("INITIAL_SYSTEM_CR (before liquidation):", INITIAL_SYSTEM_CR)
  assert INITIAL_SYSTEM_CR > MIN_ICR

  print("")

  ## Liquidate CDP
  ## Compute new values as well as profit for liquidation
  debt_to_repay = liquidation_debt_amount
  collateral_received = liquidation_collateral_amount

  console.print("=== Perform Liquidation and change state ===", style="title")
  console.print("\tThe liquidator will open a CDP with the MIN_LTV as configured, this informs the collateral_necessary\n", style="info")

  print("debt_to_repay", liquidation_debt_amount/1e18)
  print("collateral_to_recieve", collateral_received/1e18)

  collateral_necessary = debt_to_repay / price_ratio * MAX_BPS / MIN_LTV
  print("collateral_necessary", collateral_necessary/1e18)

  collateral_delta = collateral_necessary - collateral_received

  print("delta(collateral_necessary - collateral_to_recieve)", collateral_delta/1e18)

  system_coll_after_liq = TOTAL_ETH_COLL - collateral_received + collateral_necessary
  system_debt_after_liq = TOTAL_BTC_DEBT ## NOTE: Unchanged, the liquidator took the debt as their own
  print("system_coll_after_liq", system_coll_after_liq/1e18)
  print("system_debt_after_liq", system_debt_after_liq/1e18)

  SYSTEM_CR_AFTER_LIQ = system_coll_after_liq / price_ratio / system_debt_after_liq * 100
  print("SYSTEM_CR_AFTER_LIQ", SYSTEM_CR_AFTER_LIQ)

  assert SYSTEM_CR_AFTER_LIQ > INITIAL_SYSTEM_CR
  print("")

  console.print("=== Profitability Results ===",style="title")
  roi = collateral_received / (debt_to_repay * price_ratio) * 100
  print("roi for total liq", roi)

  profit = collateral_received - (debt_to_repay * price_ratio)
  print("profit for total liq", profit / 1e18)
  print("")

  ## Partial Liquidations
  ## TODO: Generalize into Range + Loops

  ## Partial Liquidation Base Case - We repay the debt and get nothing
  ## MIN Debt to repay, that would bring the CDP to MIN_ICR
  console.print("==========================================", style="title")
  console.print("===== Partial Liquidation, Best Case =====", style="title")
  console.print("==========================================\n", style="title")
  console.print("\tFind the minimum debt to repay that brings the CDP to MCR. In this case, we repay the debt and get nothing in return\n", style="info")

  maximum_debt_for_liquidatable_collateral = liquidation_collateral_amount / price_ratio / MIN_ICR * 100
  assert maximum_debt_for_liquidatable_collateral < liquidation_debt_amount

  min_partial_debt_to_liquidate_healthily = liquidation_debt_amount - maximum_debt_for_liquidatable_collateral
  
  print("If we repay at minimum", min_partial_debt_to_liquidate_healthily/1e18, "we will get a healthy CDP")

  ## SANITY CHECK FOR HEALTHY CR AFTER MIN DEBT
  new_debt_after_min_repay = maximum_debt_for_liquidatable_collateral
  new_coll_after_min_repay = liquidation_collateral_amount

  print("new_debt_after_min_repay", maximum_debt_for_liquidatable_collateral/1e18)
  print("new_coll_after_min_repay", liquidation_collateral_amount/1e18)

  ICR_AFTER_MIN_REPAY = new_coll_after_min_repay / price_ratio / new_debt_after_min_repay * 100
  print("ICR after minimum repayment is", ICR_AFTER_MIN_REPAY, " (this should be greater than MCR)")
  assert ICR_AFTER_MIN_REPAY >= MIN_ICR
  print("ICR is", ICR_AFTER_MIN_REPAY-MIN_ICR, " greater than MCR")

  print("\nThis is the base case, our profit is 0")
  print("Our price paid for out is infinite\n")
  
  ## Basically same as Full Liq, so we will skip
  max_partial = liquidation_debt_amount
  min_partial = min_partial_debt_to_liquidate_healthily

  delta = max_partial - min_partial

  print("max_partial (the full amount)", max_partial/1e18)
  print("min_partial (min repaid to get ICR >= MCR)", min_partial/1e18)
  print("delta", delta/1e18)
  print("")


  ## RANGES for Auto
  ## [25, 50, 75]
  partial_liq_ranges = range(25, 100, 25)
  console.print("======================================", style="title")
  console.print("===== Partial Liquidation Tests ======", style="title")
  console.print("======================================\n", style="title")

  for percent_partial_liq in partial_liq_ranges:
    console.print("=== Partial Liq:", percent_partial_liq ,"% of CDP ===", style="title")
    debt_to_repay = min_partial + (delta * percent_partial_liq / 100)
    debt_left_to_cdp = liquidation_debt_amount - debt_to_repay
    print(percent_partial_liq, "% liquidation")
    
    collateral_left_to_cdp = debt_left_to_cdp * price_ratio * MIN_ICR / 100
    collateral_received = liquidation_collateral_amount - collateral_left_to_cdp
    print("debt_to_repay", debt_to_repay/1e18)
    print("collateral_left_to_cdp", collateral_left_to_cdp/1e18)
    print("collateral_received", collateral_received/1e18)

    ICR_AFTER_PARTIAL_REPAY = collateral_left_to_cdp / price_ratio / debt_left_to_cdp * 100
    print("ICR_AFTER_PARTIAL_REPAY", ICR_AFTER_PARTIAL_REPAY)
    
    ## Is strictly greater because it relieves more than min repay
    assert ICR_AFTER_PARTIAL_REPAY >= MIN_ICR

    print("ASSUME WE MAGICALLY GOT THE STUFF")
    system_coll_after_partial_liq = TOTAL_ETH_COLL - collateral_received
    system_debt_after_partial_liq = TOTAL_BTC_DEBT - debt_to_repay
    
    print("\nPost Liquidation State:")
    print("system_coll_after_partial_liq", system_coll_after_partial_liq/1e18)
    print("system_debt_after_partial_liq", system_debt_after_partial_liq/1e18)

    SYSTEM_CR_AFTER_LIQ = system_coll_after_partial_liq / price_ratio / system_debt_after_partial_liq * 100
    print("SYSTEM_CR_AFTER_LIQ", SYSTEM_CR_AFTER_LIQ)

    ## It relieved some risk
    assert SYSTEM_CR_AFTER_LIQ > INITIAL_SYSTEM_CR

    ## ROI and PROFIT
    print("\nROI and Profit:")
    roi = collateral_received / (debt_to_repay * price_ratio) * 100
    print("roi", roi)

    profit = collateral_received - (debt_to_repay * price_ratio)
    print("profit in ETH", profit/1e18)
    print("")

if __name__ == '__main__':
  main()