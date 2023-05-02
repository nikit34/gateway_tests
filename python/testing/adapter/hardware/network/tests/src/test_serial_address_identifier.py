import subprocess
from unittest.mock import Mock

import pytest

from python.testing.adapter.hardware.network.serial_address_identifier import get_serial_address


class TestSerialAddressIdentifier:
    test_positive_data = [
        (
            [b"/dev/ttyUSB0\n"] + [subprocess.CalledProcessError(2, ['ls', f'/dev/ttyUSB{i}']) for i in range(1, 10)],
            "/dev/ttyUSB0"
        ), (
            [b"/dev/ttyUSB3\n"] + [subprocess.CalledProcessError(2, ['ls', f'/dev/ttyUSB{i}']) for i in range(0, 9)],
            "/dev/ttyUSB3"
        )
    ]

    test_negative_data = [
        (
            [b"/dev/ttyUSB3\n"] + [b"/dev/ttyUSB4\n"] + [subprocess.CalledProcessError(2, ['ls', f'/dev/ttyUSB{i}']) for i in range(2, 8)],
            ConnectionError("Multiple connected devices found")
        ),
        (
            [subprocess.CalledProcessError(2, ['ls', f'/dev/ttyUSB{i}']) for i in range(10)],
            ConnectionError("No connected device found")
        )
    ]

    @pytest.mark.parametrize("side_effect,expected_result", test_positive_data)
    def test_positive_get_serial_address(self, side_effect, expected_result):
        subprocess.check_output = Mock()
        subprocess.check_output.side_effect = side_effect
        assert get_serial_address() == expected_result

    @pytest.mark.parametrize("side_effect,expected_result", test_negative_data)
    def test_negative_get_serial_address(self, side_effect, expected_result):
        subprocess.check_output = Mock()
        subprocess.check_output.side_effect = side_effect
        with pytest.raises(type(expected_result), match=expected_result.args[0]):
            get_serial_address()
