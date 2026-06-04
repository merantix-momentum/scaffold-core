from omegaconf import OmegaConf

from scaffold.config_masking import MASKED_VALUE, mask_sensitive_config


def test_mask_sensitive_config_masks_sensitive_keys_and_resolvers() -> None:
    cfg = OmegaConf.create(
        {
            "api_key": "abc123",
            "db": {"password": "pw", "host": "localhost"},
            "resolver_value": "${aws_secret:my_secret}",
            "safe": "ok",
        }
    )

    masked = mask_sensitive_config(cfg)

    assert masked["api_key"] == MASKED_VALUE
    assert masked["db"]["password"] == MASKED_VALUE
    assert masked["resolver_value"] == MASKED_VALUE
    assert masked["db"]["host"] == "localhost"
    assert masked["safe"] == "ok"
