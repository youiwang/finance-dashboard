def calculate_loan(
    principal,
    annual_rate,
    months
):
    principal = float(principal)
    annual_rate = float(annual_rate)
    months = int(months)

    if principal <= 0 or months <= 0:
        return {
            "monthly_payment": 0,
            "total_payment": 0,
            "total_interest": 0,
        }

    monthly_rate = annual_rate / 12

    if monthly_rate == 0:
        payment = principal / months

    else:
        payment = (
            principal
            * monthly_rate
            * (1 + monthly_rate) ** months
            / ((1 + monthly_rate) ** months - 1)
        )

    total = payment * months

    return {
        "monthly_payment": payment,
        "total_payment": total,
        "total_interest": total - principal,
    }