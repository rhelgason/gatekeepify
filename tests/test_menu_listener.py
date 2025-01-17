import unittest
from typing import List, Union

from menu_listener.menu_listener import MenuListener
from menu_listener.menu_options import MenuOptions
from pynput import keyboard


class TestOptions(MenuOptions):
    TEST_OPTION_1 = "Option 1"
    TEST_OPTION_2 = "Option 2"
    TEST_OPTION_3 = "Option 3"
    QUIT = "Quit"


class TestMaximumOptions(MenuOptions):
    TEST_OPTION_1 = "Option 1"
    TEST_OPTION_2 = "Option 2"
    TEST_OPTION_3 = "Option 3"
    TEST_OPTION_4 = "Option 4"
    TEST_OPTION_5 = "Option 5"
    TEST_OPTION_6 = "Option 6"
    TEST_OPTION_7 = "Option 7"
    TEST_OPTION_8 = "Option 8"
    TEST_OPTION_9 = "Option 9"
    QUIT = "Quit"


class TestMenuListener(unittest.TestCase):
    test_menu: MenuListener[TestOptions]

    def setUp(self) -> None:
        self.test_menu = MenuListener[TestOptions](
            menu_options=TestOptions,
            message="Welcome to Gatekeepify! Here are our test options:",
            is_test=True,
        )

    def getMenuResponse(
        self, inputs: List[Union[keyboard.Key, keyboard.KeyCode]]
    ) -> TestOptions:
        for input in inputs:
            self.test_menu.on_press_menu_key(input)
        return list(self.test_menu.menu_options)[self.test_menu.selected_idx]

    def test_arrow_inputs_in_menu(self) -> None:
        inputs: List[Union[keyboard.Key, keyboard.KeyCode]] = [
            keyboard.Key.down,
            keyboard.Key.down,
            keyboard.Key.up,
            keyboard.Key.enter,
        ]
        self.assertEqual(self.getMenuResponse(inputs), TestOptions.TEST_OPTION_2)

    def test_number_input_in_menu(self) -> None:
        inputs: List[Union[keyboard.Key, keyboard.KeyCode]] = [
            keyboard.KeyCode.from_char("3"),
        ]
        self.assertEqual(self.getMenuResponse(inputs), TestOptions.TEST_OPTION_3)

    def test_quit_menu(self) -> None:
        inputs: List[Union[keyboard.Key, keyboard.KeyCode]] = [
            keyboard.KeyCode.from_char("q"),
        ]
        self.assertEqual(self.getMenuResponse(inputs), TestOptions.QUIT)

    def test_escape_menu(self) -> None:
        inputs: List[Union[keyboard.Key, keyboard.KeyCode]] = [keyboard.Key.esc]
        self.assertEqual(self.getMenuResponse(inputs), TestOptions.QUIT)

    def test_max_entries_exception(self) -> None:
        with self.assertRaises(Exception) as e:
            MenuListener[TestMaximumOptions](
                menu_options=TestMaximumOptions,
                message="Welcome to Gatekeepify! Here are our test options:",
                is_test=True,
            )
        self.assertEqual(
            str(e.exception), "Menu listener only currently supports 9 options."
        )
