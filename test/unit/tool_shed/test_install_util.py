from tool_shed.galaxy_install.tool_dependencies.install_util import parse_env_shell_entry


def test_parse_env_shell_entry():
    action = "prepend_to"
    expected_value = "/test/package_bwa_0_5_9/62ebd7bb637a/bwa/bin"
    line = "PATH=/test/package_bwa_0_5_9/62ebd7bb637a/bwa/bin:$PATH; export PATH"
    new_value = parse_env_shell_entry( action, "PATH", None, line )
    assert new_value == expected_value

    action = "append_to"
    line = "PATH=$PATH:/test/package_bwa_0_5_9/62ebd7bb637a/bwa/bin; export PATH"
    new_value = parse_env_shell_entry( action, "PATH", None, line )
    assert new_value == expected_value

    action = "set_to"
    line = "PATH=/test/package_bwa_0_5_9/62ebd7bb637a/bwa/bin; export PATH"
    new_value = parse_env_shell_entry( action, "PATH", None, line )
    assert new_value == expected_value

    action = "source"
    line = ". /test/package_bwa_0_5_9/62ebd7bb637a/bwa/bin"
    new_value = parse_env_shell_entry( action, "PATH", None, line )
    assert new_value == expected_value
