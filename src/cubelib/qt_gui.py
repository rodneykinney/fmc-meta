import sys
import math
import threading
import io
import logging
import traceback
import functools
from typing import Optional, List, Tuple

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QLabel, QOpenGLWidget, QLineEdit, QPushButton, QTextEdit,
                             QListWidget, QSplitter, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QSurfaceFormat

import cubelib.attempt
from cubelib.attempt import PartialSolution, Attempt
from cubelib.viz import facelet_x, facelet_y, facelet_z, axis, BACKGROUND, CubeViz
from py_cubelib import Cube, Algorithm, StepInfo, scramble as gen_scramble

# Basic set of cube moves
MOVES = {
    "R", "U", "F", "L", "D", "B",
    "R'", "U'", "F'", "L'", "D'", "B'",
    "R2", "U2", "F2", "L2", "D2", "B2",
}

NEXT_STEPS = {
    ("eo", "ud"): [("dr", "fb"), ("dr", "rl")],
    ("eo", "rl"): [("dr", "ud"), ("dr", "fb")],
    ("eo", "fb"): [("dr", "ud"), ("dr", "rl")],
    ("dr", "ud"): [("htr", "ud")],
    ("dr", "rl"): [("htr", "rl")],
    ("dr", "fb"): [("htr", "fb")],
    ("htr", "ud"): [("fr", "ud")],
    ("htr", "rl"): [("fr", "rl")],
    ("htr", "fb"): [("fr", "fb")],
    ("fr", "ud"): [("slice", "ud")],
    ("fr", "fb"): [("slice", "fb")],
    ("fr", "rl"): [("slice", "rl")],
}

PREFERRED_AXIS = {
    ("eo", "ud"): (["fb", "rl"], ["ud"]),
    ("eo", "rl"): (["ud", "fb"], ["rl"]),
    ("eo", "fb"): (["ud", "rl"], ["fb"]),
    ("*", "ud"): (["ud"], ["fb", "rl"]),
    ("*", "fb"): (["fb"], ["ud", "rl"]),
    ("*", "rl"): (["rl"], ["fb", "ud"]),
    ("*", "*"): (["ud"], ["fb", "rl"]),
}

AXIS_ORIENTATIONS = {
    ("ud", "fb"): (0, 0, 0),
    ("ud", "rl"): (0, 0, -math.pi / 2),
    ("fb", "ud"): (math.pi / 2, 0, 0),
    ("fb", "rl"): (math.pi / 2, 0, -math.pi / 2),
    ("rl", "fb"): (0, -math.pi / 2, 0),
    ("rl", "ud"): (0, -math.pi / 2, math.pi / 2),
}


class CubeGLWidget(QOpenGLWidget):
    """OpenGL widget that uses the CubeViz drawing methods"""

    def __init__(self, viz: CubeViz, parent=None):
        super(CubeGLWidget, self).__init__(parent)
        self.setMinimumSize(400, 400)

        self.viz = viz
        self.viz.attempt.add_cube_listener(self.refresh)
        self.previous_solution = self.viz.attempt.solution

        # Set up a timer for animation/updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30)  # 30ms refresh rate (approx 33 fps)

        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.dragging = False

    def set_orientation(self):
        old_sol = self.previous_solution
        new_sol = self.viz.attempt.solution

        def _get_preferred_axis(kind, variant) -> Tuple[List[str], List[str]]:
            # Options for top/bottom axis and front/back axis
            axis = PREFERRED_AXIS.get(
                (kind, variant),
                PREFERRED_AXIS.get(
                    ("*", variant),
                    PREFERRED_AXIS.get(("*", "*"))),
            )
            return axis

        if (old_sol.kind, old_sol.variant) != (new_sol.kind, new_sol.variant):
            old_top, old_front = _get_preferred_axis(old_sol.kind, old_sol.variant)
            new_top, new_front = _get_preferred_axis(new_sol.kind, new_sol.variant)
            if len(new_top) > 1:
                new_top = [f for f in old_top if f in new_top]
            if len(new_front) > 1:
                new_front = [f for f in old_front if f in new_front]
            self._set_orientation(*AXIS_ORIENTATIONS[(new_top[0], new_front[0])])

    def _set_orientation(self, x, y, z):
        self.viz.xq_angle = x
        self.viz.yq_angle = y
        self.viz.zq_angle = z


    def refresh(self):
        # Change orientation if necessary
        self.set_orientation()
        self.previous_solution = self.viz.attempt.solution

        # Repaint
        self.update()

    def initializeGL(self):
        """Initialize OpenGL settings"""
        self.viz.initializeGL(self.width(), self.height())

    def resizeGL(self, width, height):
        """Handle widget resize events"""
        self.viz.resize(width, height)

    def paintGL(self):
        """Render the OpenGL scene"""
        self.viz.draw()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def mouseMoveEvent(self, event):
        if self.dragging and self.last_mouse_pos:
            dx = event.x() - self.last_mouse_pos.x()
            self.viz.rotate(dx)
            self.last_mouse_pos = event.pos()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_X:
            self.viz.set_orientation(self.xq_angle - math.pi / 2, 0, 0)
        elif event.key() == Qt.Key_Y:
            self.viz.set_orientation(0, 0, self.zq_angle - math.pi / 2)
        elif event.key() == Qt.Key_Z:
            self.viz.set_orientation(0, self.yq_angle + math.pi / 2, 0)
        elif event.key() == Qt.Key_Left:
            self.rotate(-25)
        elif event.key() == Qt.Key_Right:
            self.rotate(25)
        else:
            super(CubeGLWidget, self).keyPressEvent(event)


NEXT_STEPS = {
    ("eo", "ud"): [("dr", "fb"), ("dr", "rl")],
    ("eo", "rl"): [("dr", "ud"), ("dr", "fb")],
    ("eo", "fb"): [("dr", "ud"), ("dr", "rl")],
    ("dr", "ud"): [("htr", "ud")],
    ("dr", "rl"): [("htr", "rl")],
    ("dr", "fb"): [("htr", "fb")],
    ("htr", "ud"): [("fr", "ud")],
    ("htr", "rl"): [("fr", "rl")],
    ("htr", "fb"): [("fr", "fb")],
    ("fr", "ud"): [("slice", "ud")],
    ("fr", "fb"): [("slice", "fb")],
    ("fr", "rl"): [("slice", "rl")],
}


class CubeExplorer(QMainWindow):
    """Main window for cube exploration with PyQt"""

    def __init__(self):
        super(CubeExplorer, self).__init__()

        self.setWindowTitle("VFMC")
        self.resize(1200, 800)

        self.attempt = Attempt()
        self.attempt.add_cube_listener(self.refresh_current_solution)
        self.attempt.add_solution_listener(self.refresh_saved_solutions)

        self.commands = Commands(self)

        self.history = []

        # Set up the OpenGL format
        gl_format = QSurfaceFormat()
        gl_format.setVersion(2, 1)
        gl_format.setProfile(QSurfaceFormat.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(gl_format)

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(2)  # Minimize spacing between components
        main_layout.setContentsMargins(4, 4, 4, 4)  # Minimize margins 
        self.setCentralWidget(central_widget)

        # Top section: GL widget + scramble/step info
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        main_layout.addWidget(top_panel)

        # Create a vertical layout for the GL widget and status labels
        gl_container = QWidget()
        gl_layout = QVBoxLayout(gl_container)
        gl_layout.setContentsMargins(0, 0, 0, 0)
        gl_layout.setSpacing(0)

        # OpenGL widget
        self.viz = CubeViz(self.attempt)
        self.gl_widget = CubeGLWidget(self.viz)
        gl_layout.addWidget(self.gl_widget)

        # Status labels below GL widget
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)

        # Left label - Step kind and variant
        self.step_label = QLabel("Step")
        self.step_label.setStyleSheet(
            "background-color: #4d4d4d; color: white; font-weight: bold; font-size: 18px; padding: 5px;")
        self.step_label.setMinimumHeight(40)
        status_layout.addWidget(self.step_label, 1)  # Give it a stretch factor of 1

        # Right label - Case name
        self.case_label = QLabel("Case")
        self.case_label.setStyleSheet(
            "background-color: #4d4d4d; color: white; font-weight: bold; font-size: 18px; padding: 5px;")
        self.case_label.setAlignment(Qt.AlignRight)
        self.case_label.setMinimumHeight(40)
        status_layout.addWidget(self.case_label, 1)  # Give it a stretch factor of 1

        gl_layout.addWidget(status_container)
        top_layout.addWidget(gl_container)

        # Scramble and step info panel (right of GL widget)
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        top_layout.addWidget(info_panel)

        current_container = QWidget()
        current_layout = QVBoxLayout(current_container)
        self.current_solution = QListWidget()
        self.current_solution.setStyleSheet("font-size: 16px;")
        current_layout.addWidget(self.current_solution)
        info_layout.addWidget(current_container)

        # Command input below the GL widget - with minimal spacing
        command_container = QWidget()
        command_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)  # Minimize vertical space
        command_layout = QHBoxLayout(command_container)
        command_layout.setContentsMargins(10, 0, 10, 0)  # Remove all margins
        command_layout.setSpacing(6)  # Minimal spacing between elements
        
        command_label = QLabel("Command:")
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.execute_command)
        help_button = QPushButton("Help")
        help_button.clicked.connect(self.show_help)

        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(help_button)
        main_layout.addWidget(command_container, 0)  # No vertical stretch

        # Status label with minimal spacing
        status_container = QWidget()
        status_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)  # Minimize vertical space
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(10, 0, 10, 0)  # Remove all margins
        status_layout.setSpacing(0)  # Remove spacing
        self.status_label = QLabel()
        self.status_label.setMaximumHeight(20)  # Limit the height
        status_layout.addWidget(self.status_label)
        main_layout.addWidget(status_container, 0)  # No vertical stretch

        # Solutions lists - make them expand to fill available vertical space
        solutions_container = QWidget()
        solutions_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        solutions_layout = QVBoxLayout(solutions_container)
        solutions_layout.setContentsMargins(10, 0, 10, 0)  # Remove margins
        solutions_layout.setSpacing(0)  # Remove vertical spacing

        # Create a horizontal layout for the solution lists
        solution_lists_layout = QHBoxLayout()
        solution_lists_layout.setSpacing(10)  # Add some spacing between columns

        # EO solutions list
        eo_container = QWidget()
        eo_layout = QVBoxLayout(eo_container)
        eo_layout.addWidget(QLabel("EO:"))
        self.eo_solution_list = QListWidget()
        self.eo_solution_list.setMinimumHeight(150)  # Set minimum height
        self.eo_solution_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.eo_solution_list.itemDoubleClicked.connect(lambda i: self.check_item("eo", i))
        eo_layout.addWidget(self.eo_solution_list)
        solution_lists_layout.addWidget(eo_container)

        # DR solutions list
        dr_container = QWidget()
        dr_layout = QVBoxLayout(dr_container)
        dr_layout.addWidget(QLabel("DR:"))
        self.dr_solution_list = QListWidget()
        self.dr_solution_list.setMinimumHeight(150)  # Set minimum height
        self.dr_solution_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dr_solution_list.itemDoubleClicked.connect(lambda i: self.check_item("dr", i))
        dr_layout.addWidget(self.dr_solution_list)
        solution_lists_layout.addWidget(dr_container)

        # HTR solutions list
        htr_container = QWidget()
        htr_layout = QVBoxLayout(htr_container)
        htr_layout.addWidget(QLabel("HTR:"))
        self.htr_solution_list = QListWidget()
        self.htr_solution_list.setMinimumHeight(150)  # Set minimum height
        self.htr_solution_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.htr_solution_list.itemDoubleClicked.connect(lambda i: self.check_item("htr", i))
        htr_layout.addWidget(self.htr_solution_list)
        solution_lists_layout.addWidget(htr_container)

        # FR solutions list
        fr_container = QWidget()
        fr_layout = QVBoxLayout(fr_container)
        fr_layout.addWidget(QLabel("FR:"))
        self.fr_solution_list = QListWidget()
        self.fr_solution_list.setMinimumHeight(150)  # Set minimum height
        self.fr_solution_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.fr_solution_list.itemDoubleClicked.connect(lambda i: self.check_item("fr", i))
        fr_layout.addWidget(self.fr_solution_list)
        solution_lists_layout.addWidget(fr_container)

        solutions_layout.addLayout(solution_lists_layout)
        main_layout.addWidget(solutions_container, 1)  # Add stretch factor of 1 to expand vertically

        # Set initial scramble
        self.generate_scramble()

        # Set focus to command input
        self.command_input.setFocus()

    def refresh_current_solution(self):
        self.current_solution.clear()
        self.current_solution.addItem(self.attempt.scramble)
        self.current_solution.addItem("")
        for step in self.attempt.solution.substeps():
            item = f"{step.alg}"
            if step.kind != "":
                if step.step_info.is_solved(self.attempt.cube):
                    item = f"{item} // {step.kind} ({step.full_alg().len()}) {step.comment}"
                else:
                    item = f"{item}{' ( )' if self.attempt.inverse else ''} // {step.kind}{step.variant}-{step.step_info.case_name(self.attempt.cube)} {step.comment}"
            self.current_solution.addItem(item)

        # Update step name
        sol = self.attempt.solution
        step_text = f"{sol.kind}{sol.variant}"
        self.step_label.setText(step_text)

        # Update case name
        if not sol.step_info.is_solved(self.attempt.cube):
            case_text = sol.step_info.case_name(self.attempt.cube)
            self.case_label.setText(case_text)
        else:
            self.case_label.setText("")

    def refresh_saved_solutions(self):
        solutions = self.attempt.solutions_by_kind()
        # EO solutions
        self.eo_solution_list.clear()
        for i, sol in enumerate(solutions.get("eo", [])):
            padding = "   " if i < 9 else ("  " if i < 99 else " ")
            self.eo_solution_list.addItem(f"{i+1}.{padding}{sol}")

        # DR solutions
        self.dr_solution_list.clear()
        for i, sol in enumerate(solutions.get("dr", [])):
            padding = "   " if i < 9 else ("  " if i < 99 else " ")
            self.dr_solution_list.addItem(f"{i+1}.{padding}{sol}")

        # HTR solutions
        self.htr_solution_list.clear()
        for i, sol in enumerate(solutions.get("htr", [])):
            padding = "   " if i < 9 else ("  " if i < 99 else " ")
            self.htr_solution_list.addItem(f"{i+1}.{padding}{sol}")

        # FR solutions
        self.fr_solution_list.clear()
        for i, sol in enumerate(solutions.get("fr", [])):
            padding = "   " if i < 9 else ("  " if i < 99 else " ")
            self.fr_solution_list.addItem(f"{i+1}.{padding}{sol}")

    def set_scramble(self, scramble: str):
        """Set the cube to a specific scramble"""
        self.attempt.set_scramble(scramble)

    def generate_scramble(self):
        """Generate a random scramble"""
        scramble = gen_scramble()
        self.set_scramble(scramble)

    def set_status(self, status: str):
        self.status_label.setText(status)

    def execute_command(self):
        """Execute a command from the command input"""
        raw_command = self.command_input.text().strip()
        cmd = raw_command
        if not cmd:
            return

        try:
            self.set_status("")
            # Check if it's a sequence of cube moves
            if all(m in MOVES for m in cmd.upper().split()):
                self._append_moves(cmd.upper())
            else:
                # Assume it's a Python command
                if cmd.find("(") < 0:
                    cmd = f"{cmd}()"
                # Use locals and globals from this context
                exec(f"self.commands.{cmd}", globals(), {'self': self})
            self.history.append(raw_command)
        except AttributeError as e:
            logging.error(traceback.format_exc())
            logging.error(sys.exc_info())
            self.set_status(f"No such command: {raw_command}")
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(sys.exc_info())
            self.set_status(f"Error: {str(e)}")

        self.command_input.clear()

    def _append_moves(self, moves):
        """Append moves to the current solution"""
        moves = moves.split(" ")
        inverse = self.attempt.inverse

        sol = self.attempt.solution

        if sol.alg.len() > 0:
            if not self.attempt.append_moves(moves, inverse):
                self.set_status(
                    f"{moves} not allowed after {sol.previous.kind}{sol.previous.variant}")
        else:
            if not self.attempt.append_moves(moves, inverse):
                assert sol.previous is not None
                if all(sol.previous.allows_move(m) for m in moves):
                    alg = sol.previous.alg
                    self.attempt.back()
                    self.attempt.append_moves(alg.normal_moves(), False)
                    self.attempt.append_moves(alg.inverse_moves(), True)
                    self.attempt.append_moves(moves, inverse)
                else:
                    self.set_status(
                        f"{moves} not allowed after {sol.previous.kind}{sol.previous.variant}")

    def set_step(self, kind, variant) -> bool:
        """Change to a specific solving step"""
        step_info = StepInfo(kind, variant)
        sol = self.attempt.solution
        past_step_kinds = {s.kind for s in sol.substeps()}
        if kind in past_step_kinds:
            # Moving backward
            while sol.kind != kind:
                sol = sol.previous
            self.attempt.set_solution(sol)
            self.attempt.advance_to(kind, variant)
            return True
        else:
            if step_info.is_eligible(self.attempt.cube):
                if (not sol.alg.is_empty()) and not sol.step_info.is_solved(self.attempt.cube):
                    self.attempt.reset()
                self.attempt.advance_to(kind, variant)
                return True
            else:
                self.set_status(f"Cube is not eligible for {kind}{variant}")
                return False

    def check_item(self, kind, item):
        index = int(item.text().split(".")[0].strip())-1
        solution = self.attempt.solutions_by_kind()[kind][index]
        self.check_solution(solution)

    def check_solution(self, solution):
        """Load a selected solution"""
        self.attempt.set_solution(solution)
        key = (self.attempt.solution.kind, self.attempt.solution.variant)
        next_steps = NEXT_STEPS.get(key)
        if next_steps:
            self.attempt.advance_to(*next_steps[0])
        self.command_input.setFocus()

    def show_help(self):
        """Show help popup with commands organized by section"""
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("VFMC Help")
        
        # Generate help text by inspecting Commands methods
        cmd = self.commands
        help_text = "<html><body style='font-family: monospace;'>"
        
        # Get all methods with their sections
        methods = []
        for name in dir(cmd):
            if name.startswith('_'):
                continue
            attr = getattr(cmd, name)
            if callable(attr) and hasattr(attr, 'section'):
                methods.append((name, attr.__doc__ or "", attr.section))
        
        # Group by section
        sections = {}
        for name, doc, section in methods:
            if section not in sections:
                sections[section] = []
            sections[section].append((name, doc))
        
        # Build formatted help text
        for section, commands in sorted(sections.items()):
            help_text += f"<h3>{section}</h3><ul>"
            for name, doc in sorted(commands):
                doc = doc.strip()
                help_text += f"<li><b>{name}</b>: {doc}</li>"
            help_text += "</ul>"
            
        help_text += "</body></html>"
        
        help_dialog.setText("Available Commands:")
        help_dialog.setInformativeText(help_text)
        help_dialog.setStandardButtons(QMessageBox.Ok)
        help_dialog.exec_()
        self.command_input.setFocus()


def main():
    # Configure logging
    logging.basicConfig(
        filename="fmc-meta.log", filemode="w",
        level=logging.DEBUG,
        format='%(levelname)s - %(message)s'
    )

    # Create the Qt Application
    app = QApplication(sys.argv)
    window = CubeExplorer()
    window.show()

    # Start the application
    sys.exit(app.exec_())


def command_section(section):
    """Decorator to categorize commands into sections for help text"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper.section = section
        return wrapper
    return decorator


class Commands:
    def __init__(self, app: CubeExplorer):
        self.app = app

    @command_section("Step Selection")
    def eoud(self):
        """Look for EO on UD axis"""
        self.app.set_step("eo", "ud")

    @command_section("Step Selection")
    def eofb(self):
        """Look for EO on FB axis"""
        self.app.set_step("eo", "fb")

    @command_section("Step Selection")
    def eorl(self):
        """Look for EO on RL axis"""
        self.app.set_step("eo", "rl")

    @command_section("Step Selection")
    def drud(self):
        """Look for DR on UD axis"""
        self.app.set_step("dr", "ud")

    @command_section("Step Selection")
    def drfb(self):
        """Look for DR on FB axis"""
        self.app.set_step("dr", "fb")

    @command_section("Step Selection")
    def drrl(self):
        """Look for DR on RL axis"""
        self.app.set_step("dr", "rl")

    @command_section("Step Selection")
    def htr(self):
        """Look for HTR"""
        sol = self.app.attempt.solution
        self.app.set_step("htr", sol.previous.variant if sol.previous else "ud")

    @command_section("Step Selection")
    def fr(self):
        """Look for FR"""
        sol = self.app.attempt.solution
        self.app.set_step("fr", sol.previous.variant if sol.previous else "ud")

    @command_section("Solution Management")
    def niss(self):
        """Switch between normal and inverse scramble"""
        self.app.attempt.set_inverse(not self.app.attempt.inverse)

    @command_section("Solution Management")
    def solve(self, num_solutions: int = 1):
        """Find and save solutions for the current step"""
        if num_solutions > 50:
            self.app.set_status("Maximum of 50 solutions per solve")
            return
        sol = self.app.attempt.solution
        on_inverse = self.app.attempt.inverse
        if on_inverse:
            self.niss()
        existing = set(str(s) for s in self.app.attempt.solutions_for_step(sol.kind, sol.variant))
        self.app.set_status(f"Finding solutions for {sol.kind}{sol.variant}...")
        algs = sol.step_info.solve(self.app.attempt.cube, len(existing) + num_solutions)
        solutions = []
        for alg in algs:
            base_alg = Algorithm(str(sol.alg))
            base_alg.merge(alg)
            s = PartialSolution(
                kind=sol.kind,
                variant=sol.variant,
                previous=sol.previous,
                alg=sol.alg.merge(alg)
            )
            if str(s) not in existing:
                solutions.append(s)
        if solutions:
            self.app.set_status(f"Found {len(solutions)} solutions to {sol.kind}{sol.variant}")
            self.app.attempt.save_solutions(solutions)
            self.app.check_solution(solutions[-1])
        else:
            self.app.set_status(f"No solutions found for {sol.kind}{sol.variant}")
        if on_inverse:
            self.app.niss()

    @command_section("Solution Management")
    def save(self):
        """Save this algorithm and start a new one"""
        sol = self.app.attempt.solution
        if not sol.step_info.is_solved(self.app.attempt.cube):
            if sol.kind == "" or sol.previous is None:
                self.app.set_status("Complete at least one step before saving")
                return
            partial = PartialSolution(
                kind=sol.previous.kind,
                variant=sol.previous.variant,
                previous=sol.previous.previous,
                alg=sol.previous.alg.merge(sol.alg),
            )
            options = NEXT_STEPS.get((partial.kind, partial.variant), [])
            case = sol.step_info.case_name(self.app.attempt.cube)
            partial.comment = f"{sol.kind}{sol.variant}-{case}" if len(options) > 1 else case
            self.app.attempt.save_solution(partial)
            self.app.refresh_saved_solutions()
            return
        self.app.attempt.save()
        next_steps = NEXT_STEPS.get((sol.kind, sol.variant))
        if next_steps is not None and len(next_steps) == 1:
            self.app.attempt.advance_to(*next_steps[0])
        else:
            self.reset()

    @command_section("Navigation")
    def reset(self):
        """Reset the cube to the beginning of the current step"""
        self.app.attempt.reset()

    @command_section("Navigation")
    def back(self):
        """Go back to the previous step"""
        self.app.attempt.back()
        
    @command_section("Scramble")
    def scramble(self):
        """
        <br>Use scramble(\"...\") to initialize with the specified scramble
        <br>or omit the parentheses to generate a new random scramble
        """
        self.app.generate_scramble()


if __name__ == "__main__":
    main()
