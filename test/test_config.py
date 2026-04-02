import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import ast
import os
import config


TESTS_PASSED = 0


def check(condition, message):
    global TESTS_PASSED
    if not condition:
        raise AssertionError(message)
    TESTS_PASSED += 1


def gather_imported_constants():
    base = os.path.dirname(os.path.dirname(__file__))
    constants = set()
    for name in [
        "elevator.py",
        "request.py",
        "fuzzy.py",
        "ga.py",
        "traffic.py",
        "simulation.py",
        "visualizer.py",
        "logger.py",
        "main.py",
    ]:
        path = os.path.join(base, name)
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "config":
                for alias in node.names:
                    if alias.name != "*":
                        constants.add(alias.name)
    return constants


def run():
    constants = gather_imported_constants()
    for c in sorted(constants):
        check(hasattr(config, c), f"Missing config constant: {c}")
        val = getattr(config, c)
        if c.startswith(("STATE_", "DIR_", "MODE_")):
            check(isinstance(val, str), f"{c} must be str")
        elif isinstance(val, (int, float, str)):
            check(True, f"{c} type ok")
        else:
            raise AssertionError(f"{c} has invalid type: {type(val).__name__}")

    check(config.FLOOR_TRAVEL_TIME > 0, "FLOOR_TRAVEL_TIME > 0")
    check(config.DOOR_OPEN_TIME > 0, "DOOR_OPEN_TIME > 0")
    check(config.DOOR_CLOSE_TIME > 0, "DOOR_CLOSE_TIME > 0")
    check(config.MAX_CAPACITY > 0, "MAX_CAPACITY > 0")

    check(0 <= config.GA_CROSSOVER_RATE <= 1, "GA_CROSSOVER_RATE in [0,1]")
    check(0 <= config.GA_MUTATION_RATE <= 1, "GA_MUTATION_RATE in [0,1]")
    check(config.GA_TOURNAMENT_SIZE <= config.GA_POPULATION, "GA_TOURNAMENT_SIZE <= GA_POPULATION")
    check(config.GA_ELITISM_COUNT < config.GA_POPULATION, "GA_ELITISM_COUNT < GA_POPULATION")

    states = [
        config.STATE_IDLE,
        config.STATE_MOVING_UP,
        config.STATE_MOVING_DOWN,
        config.STATE_DOOR_OPEN,
        config.STATE_DOOR_CLOSING,
    ]
    check(len(set(states)) == 5, "State constants are unique")

    dirs = [config.DIR_UP, config.DIR_DOWN, config.DIR_IDLE]
    check(len(set(dirs)) == 3, "Direction constants are unique")

    modes = [
        config.MODE_UP_PEAK,
        config.MODE_DOWN_PEAK,
        config.MODE_INTER_FLOOR,
        config.MODE_BALANCED,
        config.MODE_LIGHT,
    ]
    check(len(set(modes)) == 5, "Traffic mode constants are unique")

    check(
        config.FUZZY_VERY_LOW < config.FUZZY_LOW < config.FUZZY_MEDIUM < config.FUZZY_HIGH < config.FUZZY_VERY_HIGH,
        "Fuzzy levels are strictly increasing",
    )

    check(0 < config.ENERGY_REGEN_FACTOR < 1, "ENERGY_REGEN_FACTOR in (0,1)")
    check(config.SIM_TICK_SIZE > 0, "SIM_TICK_SIZE > 0")
    check(config.SIM_TICK_SIZE <= 1.0, "SIM_TICK_SIZE <= 1.0")
    check(config.TRAFFIC_WINDOW_SIZE >= 3, "TRAFFIC_WINDOW_SIZE >= 3")

    print(f"BLOCK 1 PASS: {TESTS_PASSED} tests")


if __name__ == "__main__":
    run()
