from abc import abstractmethod
from PyQt5.QtCore import QObject

class Window(object):

    def __init__(self, window, platform):
        self.platform = platform
        self.window = window
        self.connections = []

        self.window.visibleChanged.connect(self.handle_visible_changed)

    def add_connection(self, connection):
        self.connections.append(connection)

    def handle_visible_changed(self, visible):
        if visible:
            self.connect()
        else:
            self.__disconnect()

    @abstractmethod
    def connect(self):
        raise NotImplementedError()

    def __disconnect(self):
        for c in self.connections:
            QObject.disconnect(c)
    
