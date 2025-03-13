import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# U + L + F + R + B + D
facelet_x = \
    [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1]
facelet_y = \
    [-1, -1, -1, 0, 0, 0, 1, 1, 1] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [-1, -1, -1, 0, 0, 0, 1, 1, 1]
facelet_z = \
    [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5]

axis = ["xy"] * 9 \
       + ["yz"] * 9 \
       + ["xz"] * 9 \
       + ["yz"] * 9 \
       + ["xz"] * 9 \
       + ["xy"] * 9

WHITE = (1, 1, 1)
YELLOW = (1, 1, 0)
GREEN = (0, 1, 0)
BLUE = (0, 0, 1)
RED = (1, 0, 0)
ORANGE = (1, .5, 0)


class CubeViz():
    """Visualize a cube in 3D space using pygame and OpenGL"""

    def __init__(
            self,
            width=800,
            height=600,
            opacity=.6,  # Set the opacity for the colors
    ):
        # Set up the display
        self.display_width = width
        self.display_height = height
        self.opacity = opacity
        pygame.display.set_mode((self.display_width, self.display_height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Grid of Colored Squares")

        # Set up the perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.display_width / self.display_height), 0.1, 50.0)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        # Initial camera position
        self.camera_x = 0.0
        self.camera_y = -10.0
        self.camera_z = 6.0
        self.rotation_angle = -30

        self.colors = [WHITE] * 9 \
                      + [ORANGE] * 9 \
                      + [GREEN] * 9 \
                      + [RED] * 9 \
                      + [BLUE] * 9 \
                      + [YELLOW] * 9

    def draw_facelet(self, x, y, z, color, axis='xy'):
        """Draw a single face of the cube"""

        glPushMatrix()
        glTranslatef(x, y, z)
        glColor4fv(color)

        # Draw a square face
        glBegin(GL_QUADS)
        if axis == 'xy':
            glVertex3f(-0.48, -0.48, 0.0)
            glVertex3f(0.48, -0.48, 0.0)
            glVertex3f(0.48, 0.48, 0.0)
            glVertex3f(-0.48, 0.48, 0.0)
        elif axis == 'xz':
            glVertex3f(-0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, 0.48)
            glVertex3f(-0.48, 0.0, 0.48)
        elif axis == 'yz':
            glVertex3f(0.0, -0.48, -0.48)
            glVertex3f(0.0, 0.48, -0.48)
            glVertex3f(0.0, 0.48, 0.48)
            glVertex3f(0.0, -0.48, 0.48)
        glEnd()

        glPopMatrix()

    def draw(self):
        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set camera position
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.camera_x, self.camera_y, self.camera_z,  # Camera position
                  0, 0, 0,  # Look at point
                  0, 1, 0)  # Up vector

        glRotatef(self.rotation_angle, 0, 0, 1)

        """Draw facelets from back to front"""
        # D
        for i in range(45, 54):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i] + (self.opacity,), axis[i])
        # B
        for i in range(36,45):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i] + (self.opacity,), axis[i])
        # L
        for i in range(9, 18):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i] + (self.opacity,), axis[i])
        # R
        for i in range(27,36):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i] + (self.opacity,), axis[i])

        # F
        for i in range(18,27):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i] + (self.opacity,), axis[i])
        # U
        for i in range(0, 9):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i] + (self.opacity,), axis[i])

    def rotate(self, angle):
        self.rotation_angle += angle
        print(f"Rotation angle: {self.rotation_angle}")

    def move_camera(self, dx, dy, dz):
        """Move the camera position"""
        self.camera_x += dx
        self.camera_y += dy
        self.camera_z += dz
        print(f"Camera position: ({self.camera_x}, {self.camera_y}, {self.camera_z})")


def main():
    # Initialize pygame
    pygame.init()

    viz = CubeViz()
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Camera position controls
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    #viz.move_camera(0, 0, 2)
                    viz.rotate(-4)
                if event.key == pygame.K_DOWN:
                    #viz.move_camera(0, 0, -2)
                    viz.rotate(4)
                if event.key == pygame.K_LEFT:
                    viz.move_camera(-2, 0, 0)
                if event.key == pygame.K_RIGHT:
                    viz.move_camera(2, 0, 0)

        viz.draw()

        # Update the display
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
