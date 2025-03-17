import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QOpenGLWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QOpenGLContext, QSurfaceFormat
from OpenGL.GL import *

from viz import CubeViz

class OpenGLCanvas(QOpenGLWidget):
    def __init__(self, parent=None):
        super(OpenGLCanvas, self).__init__(parent)
        # Set size policy to make the widget expandable
        self.setMinimumSize(400, 300)
        self.viz = CubeViz()

    def initializeGL(self):
        # Set up the rendering context
        glClearColor(0.2, 0.3, 0.3, 1.0)
        gl_format.setProfile(QSurfaceFormat.CompatibilityProfile)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def paintGL(self):
        # gl_format.setProfile(QSurfaceFormat.CompatibilityProfile)
        # self.viz.draw()
        # pass
        # Clear the buffer
        glClear(GL_COLOR_BUFFER_BIT)

        # Draw a triangle
        glBegin(GL_TRIANGLES)
        glColor3f(1.0, 0.0, 0.0)  # Red
        glVertex3f(-0.5, -0.5, 0.0)
        glColor3f(0.0, 1.0, 0.0)  # Green
        glVertex3f(0.5, -0.5, 0.0)
        glColor3f(0.0, 0.0, 1.0)  # Blue
        glVertex3f(0.0, 0.5, 0.0)
        glEnd()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("OpenGL Canvas Example")
        self.resize(800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Add top text panel
        top_panel = QLabel("OpenGL Canvas Example - Top Panel")
        top_panel.setAlignment(Qt.AlignCenter)
        top_panel.setStyleSheet("background-color: #f0f0f0; padding: 10px; font-size: 14px;")
        layout.addWidget(top_panel)

        # Add OpenGL widget (will be centered)
        self.gl_widget = OpenGLCanvas()
        layout.addWidget(self.gl_widget, 1)  # 1 is the stretch factor, making it expand to fill space

        # Add bottom text panel
        bottom_panel = QLabel("Status: Ready - Bottom Panel")
        bottom_panel.setAlignment(Qt.AlignCenter)
        bottom_panel.setStyleSheet("background-color: #f0f0f0; padding: 10px; font-size: 14px;")
        layout.addWidget(bottom_panel)

        # Set central widget
        self.setCentralWidget(central_widget)


if __name__ == "__main__":
    # Set up the OpenGL format
    # gl_format = QSurfaceFormat()
    # gl_format.setVersion(3, 3)
    # gl_format.setProfile(QSurfaceFormat.CoreProfile)
    # QSurfaceFormat.setDefaultFormat(gl_format)

    # Set up the OpenGL format
    gl_format = QSurfaceFormat()
    # IMPORTANT: Use compatibility profile instead of core profile
    gl_format.setVersion(2, 1)
    gl_format.setProfile(QSurfaceFormat.CompatibilityProfile)
    # Setting version to 2.1 which fully supports the legacy OpenGL functions
    QSurfaceFormat.setDefaultFormat(gl_format)

    # Create and run the application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())