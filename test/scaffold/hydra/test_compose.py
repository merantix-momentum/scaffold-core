from dataclasses import field
from typing import Any, List

import hydra
import omegaconf
import pytest
from omegaconf import MISSING

from scaffold.hydra import compose
from scaffold.hydra.config_helpers import structured_config


@structured_config
class MissingConfig:
    arg1: str = MISSING
    arg2: List[int] = MISSING


@structured_config(group="/absolute/group")
class MissingConfigAbs(MissingConfig):
    arg2: List[int] = field(default_factory=lambda: [1, 2, 3])  # Use default factory for mutable values


@structured_config(group="relative")
class MissingConfigRel(MissingConfig):
    arg1: str = "rel"


@structured_config(group="subconfig")
class SubType:
    """The base class for polymorphism should not have defaults as a key"""

    conf: MissingConfig = MISSING


@structured_config(group="subconfig")
class Sub(SubType):
    defaults: List[Any] = field(default_factory=lambda: [{"/relative@conf": "MissingConfigRel"}])
    conf: MissingConfig = MISSING


@structured_config(group="sub_interpolated")
class SubInterpolated:
    interp_subvalue: str = "subvalue"


@structured_config
class MainConfig:
    defaults: List[Any] = field(
        default_factory=lambda: [
            {"subconfig": "Sub"},
            {"sub_interpolated": "${subconfig}Interpolated"},  # Interpolates to "SubInterpolated"
        ]
    )
    subconfig: SubType = MISSING
    sub_interpolated: SubInterpolated = MISSING


def test_structured_configs_can_be_composed_from_everywhere() -> None:
    """test_structured_configs_can_be_composed_from_everywhere"""
    c = compose("/MissingConfig")
    assert c == compose("MissingConfig")
    assert c == compose(MissingConfig)
    assert c == compose(MissingConfig())

    c = compose("/absolute/group/MissingConfigAbs")
    assert c == compose("absolute/group/MissingConfigAbs")
    assert c == compose(MissingConfigAbs)
    assert c == compose(MissingConfigAbs(arg1="test"))  # This triggers a warning, but doesn't make a difference

    c = compose("/relative/MissingConfigRel")
    assert c == compose("relative/MissingConfigRel")
    assert c == compose(MissingConfigRel)
    assert c == compose(MissingConfigRel())


def test_hierachical_defaults_and_overrides_with_polymorphism() -> None:
    """test_hierachical_defaults_and_overrides_with_polymorphism"""
    overrides = ["subconfig.conf.arg2=[3,4]"]
    c = compose("/MainConfig", overrides=overrides)
    assert c == compose("MainConfig", overrides=overrides)
    assert c == compose(MainConfig, overrides=overrides)
    assert c == compose(MainConfig(), overrides=overrides)
    assert list(c.keys()) == ["subconfig", "sub_interpolated"]
    assert c.sub_interpolated.interp_subvalue == "subvalue"
    assert c.subconfig.conf.arg2 == [3, 4]


def test_check_missing_value() -> None:
    """test_check_missing_value"""
    # Default hydra behavior for raising on access
    c = compose(MissingConfig)
    with pytest.raises(omegaconf.errors.MissingMandatoryValue):
        c.arg1

    # Default is checking
    with pytest.raises(omegaconf.errors.MissingMandatoryValue):
        compose(MissingConfig, check_missing=True)
    # Should not raise when provided
    compose(MissingConfig, overrides=["arg1=test", "arg2=[1, 2]"], check_missing=True)


def test_return_leaf() -> None:
    """test_return_leaf"""
    storage_args = Sub.get_store_args()
    assert storage_args["group"] == "subconfig"
    assert storage_args["name"] == "Sub"

    config = compose(Sub)
    assert config.conf.arg1 == "rel"

    config = compose(Sub, return_leaf=False)
    assert config.subconfig.conf.arg1 == "rel"


def test_compose_type_checking() -> None:
    """test_compose_type_checking"""
    exc = (omegaconf.errors.ValidationError, hydra.errors.ConfigCompositionException)
    with pytest.raises(exc):
        compose(MainConfig, overrides=["subconfig=test"])
    with pytest.raises(exc):
        compose(MainConfig, overrides=["subconfig.conf=[1, 2, 3]"])
