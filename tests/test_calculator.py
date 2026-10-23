import math
from datetime import date

import pytest

from loan_calc.calculator import (
    amortisation_schedule,
    compare_offers,
    eligible_amount,
    emi,
    format_inr,
    outstanding_after,
    prepayment_savings,
    remaining_tenure,
    schedule_to_csv,
    summary,
    total_interest,
    total_payment,
)


def test_emi_with_zero_interest():
    assert emi(1200, 0, 12) == 100.0


def test_emi_with_one_month_tenure():
    assert emi(1200, 12, 1) == 1212.0


def test_emi_with_very_large_principal_is_finite():
    result = emi(1_000_000_000_000, 7.5, 360)

    assert math.isfinite(result)
    assert result > 1_000_000_000_000 / 360


@pytest.mark.parametrize(
    ("principal", "annual_rate", "tenure_months", "message"),
    [
        (0, 5, 12, "principal must be positive"),
        (-1, 5, 12, "principal must be positive"),
        (1000, 5, 0, "tenure must be positive"),
        (1000, 5, -1, "tenure must be positive"),
    ],
)
def test_emi_rejects_invalid_principal_or_tenure(
    principal, annual_rate, tenure_months, message
):
    with pytest.raises(ValueError, match=message):
        emi(principal, annual_rate, tenure_months)


def test_total_payment_and_interest_at_zero_rate():
    assert total_payment(1200, 0, 12) == 1200.0
    assert total_interest(1200, 0, 12) == 0.0


def test_amortisation_schedule_contains_monthly_payment_breakdown():
    rows = amortisation_schedule(1000, 12, 3)

    assert len(rows) == 2
    assert rows[0] == {
        "month": 1,
        "emi": 340.02,
        "interest": 10.0,
        "principal": 330.02,
        "balance": 669.98,
    }
    assert rows[1]["month"] == 2
    assert rows[1]["balance"] < rows[0]["balance"]


def test_one_month_schedule_is_empty_in_current_implementation():
    assert amortisation_schedule(1200, 0, 1) == []


def test_outstanding_after_zero_months_returns_original_principal():
    assert outstanding_after(1000, 12, 12, 0) == 1000.0


def test_outstanding_after_more_rows_than_schedule_returns_zero():
    assert outstanding_after(1000, 12, 3, 3) == 0.0


def test_outstanding_after_returns_requested_schedule_balance():
    rows = amortisation_schedule(1000, 12, 3)

    assert outstanding_after(1000, 12, 3, 1) == rows[0]["balance"]


def test_remaining_tenure_at_zero_rate_rounds_up():
    assert remaining_tenure(1000, 0, 300) == 4


def test_remaining_tenure_for_paid_off_balance_is_zero():
    assert remaining_tenure(0, 12, 100) == 0


def test_remaining_tenure_rejects_payment_that_does_not_cover_interest():
    with pytest.raises(ValueError, match="instalment too small"):
        remaining_tenure(1000, 12, 120)


def test_prepayment_larger_than_balance_leaves_no_remaining_term():
    result = prepayment_savings(1000, 0, 10, 2, 1000)

    assert result["new_tenure"] == 2
    assert result["months_saved"] == 8


def test_compare_offers_sorts_by_total_cost():
    results = compare_offers(
        1000,
        [
            {"bank": "Higher interest", "rate": 12, "tenure": 12},
            {
                "bank": "Zero interest with fee",
                "rate": 0,
                "tenure": 12,
                "processing_fee_pct": 1,
            },
        ],
    )

    assert [offer["bank"] for offer in results] == [
        "Zero interest with fee",
        "Higher interest",
    ]
    assert results[0]["processing_fee"] == 10.0
    assert results[0]["total_cost"] < results[1]["total_cost"]


def test_eligible_amount_returns_zero_when_payment_capacity_is_exhausted():
    assert eligible_amount(1000, 500, 0, 12) == 0.0


def test_eligible_amount_at_zero_rate():
    assert eligible_amount(10_000, 1000, 0, 12) == 48_000.0


def test_format_inr_uses_indian_digit_grouping():
    assert format_inr(1_234_567.89) == "₹12,34,567.89"
    assert format_inr(-1234.5) == "-₹1,234.50"


def test_schedule_to_csv_writes_header_and_rows(tmp_path):
    output_path = tmp_path / "schedule.csv"
    rows = [
        {
            "month": 1,
            "emi": 100.0,
            "interest": 10.0,
            "principal": 90.0,
            "balance": 910.0,
        }
    ]

    schedule_to_csv(rows, str(output_path))

    assert output_path.read_text() == (
        "month,emi,interest,principal,balance\n"
        "1,100.0,10.0,90.0,910.0\n"
    )


def test_summary_uses_supplied_start_date():
    result = summary(1200, 0, 1, start=date(2024, 12, 15))

    assert result == {
        "principal": "₹1,200.00",
        "rate": "0% p.a.",
        "tenure": "1 months",
        "emi": "₹1,200.00",
        "total_interest": "₹0.00",
        "total_payment": "₹1,200.00",
        "last_emi": "2025-01",
        "currency": "INR",
    }