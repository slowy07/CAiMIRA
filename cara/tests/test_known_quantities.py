import numpy as np
import numpy.testing as npt
import pytest

import cara.models as models


def test_no_mask_aerosols(baseline_model):
    exp = models.Expiration.types['Unmodulated Vocalization']
    npt.assert_allclose(
        exp.aerosols(models.Mask.types['No mask']),
        6.077541e-12,
        rtol=1e-5,
    )


def test_no_mask_emission_rate(baseline_model):
    rate = 167.74011998223307
    npt.assert_allclose(
        [baseline_model.infected.emission_rate(t) for t in [0, 1, 4, 4.5, 5, 8, 9]],
        [0, rate, rate, 0, 0, rate, 0],
        rtol=1e-5
    )


@pytest.fixture
def baseline_model():
    model = models.Model(
        room=models.Room(volume=75),
        ventilation=models.WindowOpening(
            active=models.PeriodicInterval(period=120, duration=120),
            inside_temp=293, outside_temp=283, cd_b=0.6,
            window_height=1.6, opening_length=0.6,
        ),
        infected=models.InfectedPerson(
            virus=models.Virus.types['SARS_CoV_2'],
            presence=models.SpecificInterval(((0, 4), (5, 8))),
            mask=models.Mask.types['No mask'],
            activity=models.Activity.types['Light exercise'],
            expiration=models.Expiration.types['Unmodulated Vocalization'],
        ),
        infected_occupants=1,
        exposed_occupants=10,
        exposed_activity=models.Activity.types['Light exercise'],
    )
    return model


@pytest.fixture
def baseline_periodic_window():
    return models.WindowOpening(
        active=models.PeriodicInterval(period=120, duration=15),
        inside_temp=293, outside_temp=283, cd_b=0.6,
        window_height=1.6, opening_length=0.6,
    )


@pytest.fixture
def baseline_room():
    return models.Room(volume=75)


@pytest.fixture
def baseline_periodic_hepa():
    return models.HEPAFilter(
        active=models.PeriodicInterval(period=120, duration=15),
        q_air_mech=514.74,
    )


def test_concentrations(baseline_model):
    ts = [0, 4, 5, 7, 10]
    concentrations = [baseline_model.concentration(t) for t in ts]
    npt.assert_allclose(
        concentrations,
        [0.000000e+00, 2.891970e-01, 1.266287e-04, 2.891969e-01, 5.544607e-08],
        rtol=1e-5
    )


def test_smooth_concentrations(baseline_model):
    # We don't care about the actual concentrations in this test, but rather
    # that the curve itself is smooth.
    dx = 0.1
    dy_limit = dx * 2  # Anything more than this is a bit steep.
    ts = np.arange(0, 10, dx)
    concentrations = [baseline_model.concentration(t) for t in ts]
    assert np.abs(np.diff(concentrations)).max() < dy_limit


def build_model(interval_duration):
    model = models.Model(
        room=models.Room(volume=75),
        ventilation=models.HEPAFilter(
            active=models.PeriodicInterval(period=120, duration=interval_duration),
            q_air_mech=500.,
        ),
        infected=models.InfectedPerson(
            virus=models.Virus.types['SARS_CoV_2'],
            presence=models.SpecificInterval(((0, 4), (5, 8))),
            mask=models.Mask.types['No mask'],
            activity=models.Activity.types['Light exercise'],
            expiration=models.Expiration.types['Unmodulated Vocalization'],
        ),
        infected_occupants=1,
        exposed_occupants=10,
        exposed_activity=models.Activity.types['Light exercise'],
    )
    return model


def test_concentrations_startup(baseline_model):
    # The concentrations should be the same until the beginning of the
    # first time that the ventilation is disabled.
    m1 = build_model(interval_duration=120)
    m2 = build_model(interval_duration=65)

    assert m1.concentration(1.) == m2.concentration(1.)


def test_r0(baseline_model):
    p = baseline_model.infection_probability()
    npt.assert_allclose(p, 93.196908)


def test_periodic_window(baseline_periodic_window, baseline_room):
    # Interesting transition times for a period of 120 and duration of 15.
    ts = [0, 14/60, 15/60, 16/60, 119/60, 120/60, 121/60, 239/60, 240/60]
    aes = [baseline_periodic_window.air_exchange(baseline_room, t) for t in ts]
    rate = 6.86347
    answers = [0, rate, rate, 0, 0, 0, rate, 0, 0]
    npt.assert_allclose(aes, answers, rtol=1e-5)


def test_periodic_hepa(baseline_periodic_hepa, baseline_room):
    # Interesting transition times for a period of 120 and duration of 15.
    ts = [0, 14 / 60, 15 / 60, 16 / 60, 119 / 60, 120 / 60, 121 / 60, 239 / 60, 240 / 60]
    rate = 514.74 / 75
    aes = [baseline_periodic_hepa.air_exchange(baseline_room, t) for t in ts]
    answers = [0, rate, rate, 0, 0, 0, rate, 0, 0]
    npt.assert_allclose(aes, answers, rtol=1e-5)


def test_expiration_aerosols():
    mask = models.Mask.types['Type I']
    exp1 = models.Expiration((0.751, 0.139, 0.0139, 0.059),
                            particle_sizes = (0.8e-4, 1.8e-4, 3.5e-4, 5.5e-4))
    exp2 = models.Expiration((0.059, 0.0139, 0.751, 0.139),
                            particle_sizes = (5.5e-4, 3.5e-4, 0.8e-4, 1.8e-4))
    npt.assert_allclose(exp1.aerosols(mask), exp2.aerosols(mask), rtol=1e-5)


def test_piecewiseconstantfunction_wrongarguments():
    # number of values should be 1+number of transition times
    pytest.raises(ValueError,models.PiecewiseconstantFunction,[0,1],[0,0])
    pytest.raises(ValueError,models.PiecewiseconstantFunction,[0],[0,0])
    # two transition times cannot be equal
    pytest.raises(ValueError,models.PiecewiseconstantFunction,[0,2,2],[0,0])
    # unsorted transition times are not allowed
    pytest.raises(ValueError,models.PiecewiseconstantFunction,[2,0],[0,0])


def test_piecewiseconstantfunction():
    transition_times = [0,8,16,24]
    values = [2,5,8]
    fun = models.PiecewiseconstantFunction(transition_times,values)
    assert (fun.value(10) == 5) and (fun.value(20.5) == 8) and \
            (fun.value(8) == 2) and (fun.value(0) == 2) and (fun.value(24) == 8)


def test_constantfunction():
    transition_times = [0,24]
    values = [20]
    fun = models.PiecewiseconstantFunction(transition_times,values)
    for t in [0,1,8,10,16,20.1,24]:
        assert (fun.value(t) == 20)


def test_piecewiseconstantfunction_vs_interval():
    transition_times = [0,8,16,24]
    values = [0,1,0]
    fun = models.PiecewiseconstantFunction(transition_times,values)
    interval = models.SpecificInterval(present_times=[(8,16)])
    assert interval.transition_times() == fun.interval().transition_times()
    for t in [0,1,8,10,16,20.1,24]:
        assert fun.interval().triggered(t) == interval.triggered(t)


def test_windowopening():
    w1 = models.WindowOpening(active=models.SpecificInterval([(0,24)]),
                inside_temp=293.15,outside_temp=283.15,
                window_height=1.,opening_length=0.6)
    w2 = models.WindowOpening(active=models.SpecificInterval([(0,24)]),
                inside_temp=293.15,outside_temp=273.15,
                window_height=1.,opening_length=0.6)
    npt.assert_allclose(w1.air_exchange(models.Room(volume=68),10.),
                        3.7393925,rtol=1e-5)
    npt.assert_allclose(w2.air_exchange(models.Room(volume=68),10.),
                        5.3842316,rtol=1e-5)

