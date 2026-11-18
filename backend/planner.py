"""Business planner: five-year customer value, payback and the value of better retention."""


def _num(d, key, lo, hi, default):
    try:
        v = float(d.get(key, default))
    except (TypeError, ValueError):
        v = default
    return min(max(v, lo), hi)


def calc(d):
    n = _num(d, "customers", 1, 1e8, 5000)
    aov = _num(d, "aov", 0, 1e6, 80)
    orders = _num(d, "orders_per_year", 0, 365, 4)
    cac = _num(d, "cac", 0, 1e6, 60)
    margin = _num(d, "margin", 1, 100, 35) / 100
    ret = _num(d, "retention", 1, 99, 60) / 100
    uplift = _num(d, "uplift", 0, 30, 5) / 100
    disc, years = 0.10, 5
    ann = aov * orders * margin
    ret2 = min(0.99, ret + uplift)

    def cum(r):
        total, out = -cac, [-cac]
        for t in range(years):
            total += ann * r ** t / (1 + disc) ** t
            out.append(round(total, 2))
        return out

    today, better = cum(ret), cum(ret2)
    ltv, ltv2 = today[-1] + cac, better[-1] + cac
    ratio = ltv / cac if cac else 0.0
    verdict = "Healthy" if ratio >= 3 else "Needs work" if ratio >= 1 else "Losing money"
    return {"ltv": round(ltv, 2), "ltv_improved": round(ltv2, 2), "ratio": round(ratio, 2), "verdict": verdict,
            "payback_months": round(cac / (ann / 12), 1) if ann else None,
            "base_total": round(ltv * n), "gain_total": round((ltv2 - ltv) * n),
            "series_today": today, "series_improved": better,
            "inputs": {"customers": n, "aov": aov, "orders_per_year": orders, "cac": cac,
                       "margin": margin * 100, "retention": ret * 100, "uplift": uplift * 100}}
