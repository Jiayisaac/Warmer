"""Sourdough warmer application entry point."""
import signal
from controller import WarmerController


def main():
    controller = WarmerController()
    previous = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda signum, frame: controller.stop())
    try:
        controller.start()
        controller.run()
    finally:
        controller.shutdown()
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    main()
