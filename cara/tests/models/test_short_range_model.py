import typing

import numpy as np
import pytest

from cara import models
import cara.monte_carlo as mc_models
from cara.apps.calculator.model_generator import build_expiration
from cara.monte_carlo.data import dilution_factor, short_range_expiration_distributions


@pytest.fixture
def concentration_model() -> mc_models.ConcentrationModel:
    return mc_models.ConcentrationModel(
        room=models.Room(volume=75),
        ventilation=models.AirChange(
            active=models.SpecificInterval(present_times=((8.5, 12.5), (13.5, 17.5))),
            air_exch=30.,
        ),
        infected=mc_models.InfectedPopulation(
            number=1,
            virus=models.Virus.types['SARS_CoV_2'],
            presence=models.SpecificInterval(present_times=((8.5, 12.5), (13.5, 17.5))),
            mask=models.Mask.types['No mask'],
            activity=models.Activity.types['Light activity'],
            expiration=build_expiration({'Speaking': 0.33, 'Breathing': 0.67}),
            host_immunity=0.,
        ),
        evaporation_factor=0.3,
    )


@pytest.fixture
def presences() -> typing.Tuple[typing.Tuple[str, models.SpecificInterval], ...]:
    return (
        ('Breathing', models.SpecificInterval((10.5, 11.0))),
        ('Speaking', models.SpecificInterval((14.5, 15.0))),
        ('Shouting', models.SpecificInterval((16.5, 17.5))),
    )


@pytest.fixture
def expirations(presences) -> typing.Tuple[mc_models.Expiration, ...]:
    # Monte carlo expirations! So build model.
    return tuple(short_range_expiration_distributions[activity] for (activity, presence) in presences)


@pytest.fixture
def dilutions(presences):
    return dilution_factor(activities=[activity for (activity, presence) in presences])


def test_short_range_model_ndarray(concentration_model, presences, expirations, dilutions):
    concentration_model = concentration_model.build_model(250_000)
    model = mc_models.ShortRangeModel(presences, expirations, dilutions)
    model = model.build_model(250_000)
    assert isinstance(model._normed_concentration(concentration_model, 10.75), np.ndarray)
    assert isinstance(model.short_range_concentration(concentration_model, 14.75), np.ndarray)
    assert isinstance(model.normed_exposure_between_bounds(concentration_model, 16.6, 17.5), np.ndarray) 


@pytest.mark.parametrize(
    "start, stop, expected_exposure", [
        [8.5, 12.5, 5.963061627547172e-10],
        [10.5, 11.0,  5.934552264225482e-10],
        [10.6, 11.9, 4.709684623109963e-10],
    ]
)
def test_normed_exposure_between_bounds(
        start, stop, expected_exposure, concentration_model,
        presences, expirations, dilutions):
    concentration_model = concentration_model.build_model(250_000)
    model = mc_models.ShortRangeModel(presences, expirations, dilutions)
    model = model.build_model(250_000)
    np.testing.assert_almost_equal(
        model.normed_exposure_between_bounds(concentration_model, start, stop).mean(), expected_exposure, decimal=10
    )


@pytest.mark.parametrize(
    "time, expected_sr_normed_concentration, expected_concentration", [
        [10.75, 1.1670056689678455e-08, 1.1731466540816526],
        # [14.75, 3.6414877020308386e-06, 474.36376505412574],
        # [16.75, 1.973757599365769e-05, 2850.6219623225024],
    ]
)
def test_short_range_model(
        time, expected_sr_normed_concentration, expected_concentration,
        concentration_model, presences, expirations, dilutions,
):
    concentration_model = concentration_model.build_model(250_000)
    model = mc_models.ShortRangeModel(presences, expirations, dilutions)
    model = model.build_model(250_000)
    np.testing.assert_almost_equal(
        model._normed_concentration(concentration_model, time).mean(), expected_sr_normed_concentration, decimal=0
    )
    np.testing.assert_almost_equal(
        model.short_range_concentration(concentration_model, time).mean(), expected_concentration, decimal=0
    )
