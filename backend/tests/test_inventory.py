from datetime import date, datetime, time, timedelta

from app.inventory import estimate

TODAY = date(2026, 10, 3)


def days_ago(*ns):
    return [TODAY - timedelta(days=n) for n in ns]


def test_frisch_gekauft_ist_gruen():
    e = estimate(days_ago(0), shelf_days=7, use_days=7, today=TODAY)
    assert (e.status, e.remaining, e.visible) == ("gruen", 1.0, True)


def test_haltbarkeit_begrenzt_wenn_kuerzer_als_verbrauch():
    e = estimate(days_ago(30, 20, 10, 5), shelf_days=3, use_days=7, today=TODAY)
    assert e.expected_days == 3
    assert e.status == "rot" and e.expired


def test_eigenes_intervall_erst_ab_drei_kaeufen():
    assert estimate(days_ago(2, 0), 180, 30, TODAY).expected_days == 30
    e = estimate(days_ago(20, 10, 0), 180, 30, TODAY)
    assert (e.interval_days, e.expected_days) == (10, 10)


def test_letztes_drittel_ist_gelb():
    # Intervalle 9 und 21 -> Median 15
    assert estimate(days_ago(37, 28, 7), 365, 14, TODAY).status == "gruen"  # Rest 0,53
    assert estimate(days_ago(42, 33, 12), 365, 14, TODAY).status == "gelb"  # Rest 0,2


def test_rot_verschwindet_nach_karenzzeit():
    assert estimate(days_ago(8), 7, 7, TODAY).visible
    assert not estimate(days_ago(11), 7, 7, TODAY).visible


def at(n, hour=12):
    return datetime.combine(TODAY - timedelta(days=n), time(hour))


def test_aufgebraucht_blendet_aus_bis_zum_naechsten_kauf():
    e = estimate([at(2)], 7, 7, TODAY, [(at(1), "used_up")])
    assert (e.status, e.visible, e.correction_days) == ("weg", False, 1)
    e = estimate([at(2), at(0, 18)], 7, 7, TODAY, [(at(1), "used_up")])
    assert e.status == "gruen" and e.correction is None


def test_aufgebraucht_trainiert_die_verbrauchsdauer():
    # Standard wäre 7 Tage, zweimal nach 3 Tagen aufgebraucht -> 3 Tage
    bought = [at(20), at(10), at(1)]
    fixes = [(at(17), "used_up"), (at(7), "used_up")]
    e = estimate(bought, 30, 7, TODAY, fixes)
    assert e.learned_days == 3 and e.expected_days == 3


def test_noch_da_gibt_neue_frist_aber_nicht_ueber_haltbarkeit():
    e = estimate([at(9)], 30, 7, TODAY, [(at(0), "still_there")])
    assert (e.status, e.visible, e.days_left) == ("gruen", True, 4)
    e = estimate([at(9)], 8, 7, TODAY, [(at(0), "still_there")])
    assert e.status == "rot" and e.expired
