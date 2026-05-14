import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from app.application import MySourceTreeApplication


def main():
    app = MySourceTreeApplication()
    sys.exit(app.run(sys.argv))


if __name__ == '__main__':
    main()