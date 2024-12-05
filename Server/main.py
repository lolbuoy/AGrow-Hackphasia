from multiprocessing import Process
from src.server import run_server
from src.mqtt import run_mqtt


def main():
    p1 = Process(target=run_server)
    p2 = Process(target=run_mqtt)

    p1.start()
    p2.start()

    p1.join()
    p2.join()


if __name__ == "__main__":
    main()
