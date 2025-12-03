"""
Applicazione principale
"""
from gui.main_window import MainWindow


def main():
    """Punto di ingresso dell'applicazione modifica"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()