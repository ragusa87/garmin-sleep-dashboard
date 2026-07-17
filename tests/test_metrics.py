from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from garmin_sleep.metrics import (
    bedtime_offset_min,
    bedtime_std_minutes,
    correlate,
    feedback_frequencies,
    night_metrics,
    pearson,
    rolling_mean,
    sleep_hr_elevation,
    social_jetlag_min,
    weekday_profile,
)
from garmin_sleep.models import DailySummary, SleepNight, SleepScores

ZURICH = ZoneInfo("Europe/Zurich")


def make_night(cal, start, end, **kw):
    defaults = dict(deep_s=3600, light_s=7200, rem_s=3600, awake_s=1800)
    defaults.update(kw)
    return SleepNight(
        calendar_date=cal,
        start_gmt=start,
        end_gmt=end,
        **defaults,
    )


def test_night_metrics_hand_computed():
    # Nuit d'été (DST) : 22:00 UTC = minuit à Zurich (UTC+2)
    n = make_night(
        date(2026, 7, 2),
        datetime(2026, 7, 1, 22, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 2, 6, 0, tzinfo=timezone.utc),
    )
    m = night_metrics(n, ZURICH)
    assert m.total_h == 4.0  # 3600+7200+3600 s
    assert m.deep_pct == 25.0
    assert m.light_pct == 50.0
    assert m.rem_pct == 25.0
    assert m.awake_pct == 100 * 1800 / (8 * 3600)
    assert m.bedtime_local.hour == 0 and m.bedtime_local.day == 2
    assert m.wake_local.hour == 8
    assert m.midsleep_local.hour == 4


def test_night_metrics_rem_none():
    n = make_night(
        date(2026, 1, 2),
        datetime(2026, 1, 1, 22, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 6, 0, tzinfo=timezone.utc),
        rem_s=None,
    )
    m = night_metrics(n, ZURICH)
    assert m.rem_pct is None
    assert m.deep_pct == 100 * 3600 / 10800
    # Hiver : UTC+1
    assert m.bedtime_local.hour == 23


def test_bedtime_offset_circular():
    d1 = datetime(2026, 1, 1, 23, 30)
    d2 = datetime(2026, 1, 2, 0, 30)
    o1, o2 = bedtime_offset_min(d1), bedtime_offset_min(d2)
    assert abs(o2 - o1) == 60  # adjacents malgré le passage de minuit
    assert bedtime_offset_min(datetime(2026, 1, 1, 18, 0)) == 0


def test_bedtime_std_mixed_midnight():
    nights = [
        make_night(
            date(2026, 1, i + 2),
            # alternance 23:30 / 00:30 heure de Zurich (UTC+1) => 22:30 / 23:30 UTC
            datetime(2026, 1, i + 1, 22 + (i % 2), 30, tzinfo=timezone.utc),
            datetime(2026, 1, i + 2, 6, 0, tzinfo=timezone.utc),
        )
        for i in range(4)
    ]
    std = bedtime_std_minutes(nights, ZURICH)
    assert std is not None and std < 60  # pas ~700 min comme avec un axe naïf


def test_rolling_mean_window():
    series = [(date(2026, 1, i), float(i)) for i in range(1, 11)]
    out = rolling_mean(series, 3)
    assert out[0] == (date(2026, 1, 1), 1.0)
    # jour 10 : fenêtre 8,9,10
    assert out[-1] == (date(2026, 1, 10), 9.0)


def test_pearson_guards():
    assert pearson([(1.0, 1.0)] * 5, min_n=14) is None  # trop peu de points
    assert pearson([(1.0, float(i)) for i in range(20)], min_n=14) is None  # variance nulle
    r = pearson([(float(i), float(i)) for i in range(20)], min_n=14)
    assert abs(r - 1.0) < 1e-9


def test_correlate_prev_day_alignment():
    # 20 nuits ; steps du jour J-1 parfaitement corrélés à la durée de la nuit J
    nights, days = [], {}
    for i in range(20):
        cal = date(2026, 3, 1) + timedelta(days=i)
        prev = cal - timedelta(days=1)
        nights.append(
            make_night(
                cal,
                datetime.combine(prev, time(22, 0), tzinfo=timezone.utc),
                datetime.combine(cal, time(6, 0), tzinfo=timezone.utc),
                deep_s=3600 + i * 360,
                light_s=0,
                rem_s=0,
                scores=SleepScores(overall=50 + i),
            )
        )
        days[prev] = DailySummary(calendar_date=prev, steps=1000 + i * 100)
    rows = {(r.variable, r.target): r for r in correlate(nights, days)}
    r_steps = rows[("steps", "total_h")]
    assert r_steps.n == 20
    assert abs(r_steps.r - 1.0) < 1e-9
    assert rows[("avg_stress", "score")].n == 0
    assert rows[("avg_stress", "score")].r is None


def test_social_jetlag_and_weekday_profile():
    nights = []
    for i in range(14):
        cal = date(2026, 3, 2 + i)  # 2026-03-02 = lundi
        late = 2 if cal.weekday() >= 5 else 0  # coucher 2 h plus tard le week-end
        nights.append(
            make_night(
                cal,
                datetime(2026, 3, 1 + i, 21 + late, 0, tzinfo=timezone.utc),
                datetime(2026, 3, 2 + i, 5 + late, 0, tzinfo=timezone.utc),
            )
        )
    jl = social_jetlag_min(nights, ZURICH)
    assert jl is not None and abs(jl - 120) < 1
    profile = weekday_profile(nights, ZURICH)
    assert len(profile) == 7
    assert all(p.n == 2 for p in profile)


def test_feedback_frequencies():
    nights = [
        make_night(
            date(2026, 1, i + 1),
            datetime(2026, 1, i + 1, 22, 0, tzinfo=timezone.utc),
            datetime(2026, 1, i + 2, 6, 0, tzinfo=timezone.utc),
            scores=SleepScores(feedback="NEGATIVE_NOT_ENOUGH_REM", insight="NONE"),
        )
        for i in range(4)
    ]
    freq = feedback_frequencies(nights)
    assert freq == {"NEGATIVE_NOT_ENOUGH_REM": 1.0}


def test_sleep_hr_elevation():
    days = {
        date(2026, 1, i + 1): DailySummary(calendar_date=date(2026, 1, i + 1), resting_hr=50)
        for i in range(15)
    }
    nights = [
        make_night(
            date(2026, 1, 15),
            datetime(2026, 1, 14, 22, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 15, 6, 0, tzinfo=timezone.utc),
            avg_sleep_hr=62.0,
        )
    ]
    [(d, elev)] = sleep_hr_elevation(nights, days)
    assert d == date(2026, 1, 15)
    assert elev == 12.0


def test_monthly_spo2():
    nights = []
    # mars : 2 nuits (min 82, 90) ; avril : 1 nuit (min 79)
    for d, low in [(date(2026, 3, 5), 82), (date(2026, 3, 20), 90), (date(2026, 4, 2), 79)]:
        nights.append(
            make_night(
                d,
                datetime(d.year, d.month, d.day - 1, 22, 0, tzinfo=timezone.utc),
                datetime(d.year, d.month, d.day, 6, 0, tzinfo=timezone.utc),
                avg_spo2=94.0,
                lowest_spo2=low,
            )
        )
    # nuit sans SpO2 : ignorée
    nights.append(
        make_night(
            date(2026, 3, 10),
            datetime(2026, 3, 9, 22, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 10, 6, 0, tzinfo=timezone.utc),
        )
    )
    from garmin_sleep.metrics import monthly_spo2

    months = monthly_spo2(nights)
    assert [m.month for m in months] == ["2026-03", "2026-04"]
    mars, avril = months
    assert mars.n == 2
    assert mars.share_below_85 == 0.5
    assert mars.share_below_80 == 0.0
    assert mars.median_lowest == 86.0
    assert avril.share_below_80 == 1.0


def test_low_spo2_share_window():
    from garmin_sleep.metrics import low_spo2_share

    nights = [
        make_night(
            date(2026, 3, 1 + i),
            datetime(2026, 3, 1 + i, 22, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 2 + i, 6, 0, tzinfo=timezone.utc),
            lowest_spo2=80 if i < 5 else 90,
        )
        for i in range(10)
    ]
    share, n = low_spo2_share(nights, date(2026, 3, 1), date(2026, 3, 5))
    assert (share, n) == (1.0, 5)
    share, n = low_spo2_share(nights, date(2026, 3, 6), date(2026, 3, 10))
    assert (share, n) == (0.0, 5)
    share, n = low_spo2_share(nights, date(2026, 5, 1), date(2026, 5, 30))
    assert (share, n) == (None, 0)
