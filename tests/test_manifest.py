from wechat_agent_channel.defaults import create_default_registry


def test_default_registry_lists_all_implemented_channels():
    registry = create_default_registry()
    assert {item.type for item in registry.list()} == {
        "official_account", "wechat_kf", "wecom_aibot", "clawbot"
    }


def test_legacy_flag_can_limit_registry_to_official_account():
    assert [item.type for item in create_default_registry(include_planned=False).list()] == ["official_account"]
