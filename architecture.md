# Loan Calculator Function Guide

This document describes the public helpers and internal rate conversion in `loan_calc/calculator.py`. The module uses INR as its default currency and represents rates as annual percentages (for example, `9` means 9% per year), except where noted below.

## Calculation flow

`emi` is the central payment calculation. `total_payment` and `total_interest` build on it. `amortisation_schedule` calculates period-by-period balances; `outstanding_after` reads a balance from that schedule. `prepayment_savings` combines the schedule with `remaining_tenure`. `compare_offers` and `eligible_amount` use the same EMI math for comparisons and borrowing capacity. `format_inr`, `schedule_to_csv`, and `summary` prepare results for display or export.

## Functions

### `_monthly_rate(annual_rate)`

Converts an annual percentage rate into a monthly decimal rate by dividing by 1,200, then rounds the result to four decimal places. For example, 12% becomes `0.01` per month. The rounding happens before the other calculations, so it can affect results, especially at low rates. This is an internal helper.

### `emi(principal, annual_rate, tenure_months)`

Calculates the fixed monthly instalment using the standard amortizing-loan formula and returns it rounded to two decimal places. `principal` must be positive and `tenure_months` must be positive; otherwise it raises `ValueError`. A zero monthly rate is handled by dividing the principal evenly over the term.

### `total_payment(principal, annual_rate, tenure_months)`

Returns the EMI multiplied by the number of months, rounded to two decimal places. It uses the already-rounded EMI, so this is the total of equal instalments rather than a separately recalculated exact payment total.

### `total_interest(principal, annual_rate, tenure_months)`

Returns `total_payment - principal`, rounded to two decimal places. It inherits the validation and rounding behavior of `emi` and `total_payment`.

### `amortisation_schedule(principal, annual_rate, tenure_months)`

Builds a list of monthly schedule rows. Each row is a dictionary with `month`, `emi`, `interest`, `principal`, and `balance`. Interest and principal portions are rounded to two decimals, and the displayed balance is clamped to at least zero.

**Current implementation caveat:** the loop runs from month 1 up to, but not including, `tenure_months`. Thus the returned schedule has `tenure_months - 1` rows and omits the final instalment. The code contains a special case for the final month inside this loop, but that condition is unreachable. A one-month loan therefore produces an empty schedule.

### `outstanding_after(principal, annual_rate, tenure_months, months_paid)`

Returns the schedule balance after the requested number of payments. For `months_paid <= 0`, it returns the starting principal rounded to two decimals. If `months_paid` exceeds the number of schedule rows, it returns `0.0`; otherwise it indexes the corresponding row. Because the schedule omits its final month, requesting the balance after the full term returns zero through this out-of-range behavior, rather than from a final schedule row.

### `remaining_tenure(balance, annual_rate, instalment)`

Estimates how many whole monthly instalments are needed to repay a balance, rounding the formula's result up with `ceil`. It returns zero for a non-positive balance. If the computed rate is zero, it uses `ceil(balance / instalment)`. It raises `ValueError` when the instalment is no greater than the balance multiplied by the rate, since the balance would not be paid down.

**Current implementation caveat:** unlike `_monthly_rate`, this function sets the rate to `annual_rate / 100` and uses that value as a monthly rate. It does not divide by 12 or apply the four-decimal rounding, so its rate units differ from the rest of the module and can substantially change the result. The zero-rate branch also requires a nonzero instalment to avoid division by zero.

### `prepayment_savings(principal, annual_rate, tenure_months, prepay_month, prepay_amount)`

Estimates savings from making a lump-sum payment after a specified month while keeping the original EMI and shortening the remaining term. It returns a dictionary containing the EMI, months saved, estimated new total tenure, interest saved, and interest paid before prepayment.

The function looks up the balance at `prepay_month` in the amortisation schedule, subtracts the prepayment, and calls `remaining_tenure` for the reduced balance. As a result, it inherits both the schedule's missing final row and `remaining_tenure`'s rate-unit caveat. The code does not validate `prepay_month` or `prepay_amount`; an invalid month can raise `IndexError`, and a prepayment greater than the balance is treated as fully paying off the loan.

### `compare_offers(principal, offers)`

Calculates an EMI, total interest, processing fee, and total cost for each offer, then sorts the returned list from lowest to highest total cost. Each offer must provide `bank`, `rate`, and `tenure`; `processing_fee_pct` is optional and defaults to zero. The fee is calculated as a percentage of the principal, and total cost is interest plus fee (the principal itself is not included). Invalid loan inputs can raise the same `ValueError` as `emi`; missing required offer keys raise `KeyError`.

### `eligible_amount(monthly_income, existing_emis, annual_rate, tenure_months, foir=0.5)`

Estimates the principal supported by the available monthly payment. Available capacity is `monthly_income * foir - existing_emis`; if it is zero or below, the function returns `0.0`. Otherwise, it inverts the EMI formula using `_monthly_rate` and returns the estimated principal rounded to two decimals. `foir` is the fraction of income allowed for all EMIs (50% by default). This function does not independently validate the term, rate, or income inputs.

### `format_inr(amount)`

Formats a number with the rupee symbol, two decimal places, and Indian digit grouping (for example, `₹12,34,567.89`). Negative values receive a leading minus sign. It rounds to two decimals before formatting.

### `schedule_to_csv(rows, path)`

Writes schedule dictionaries to a CSV-formatted text file at `path`, with columns `month,emi,interest,principal,balance`. It expects every row to contain those keys. The file is opened in write mode, so an existing file at that path is replaced. The function does not return a value.

### `summary(principal, annual_rate, tenure_months, start=None)`

Returns a display-ready dictionary containing formatted principal, EMI, total interest, and total payment, plus the rate, tenure, estimated last-EMI year and month, and currency code. If `start` is omitted, it uses the current date; otherwise it expects an object with `year` and `month`, such as `datetime.date`. The last EMI date is computed by advancing the start month by `tenure_months`. Currency formatting uses the module's `DEFAULT_CURRENCY` (`INR`).

## Module constant

### `DEFAULT_CURRENCY`

The currency code `INR`, included in the result from `summary`. `format_inr` also hardcodes the rupee symbol rather than reading this constant.