import sys
import math
import threading
import io
import logging
import traceback
from typing import Optional, List

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                           QLabel, QOpenGLWidget, QLineEdit, QPushButton, QTextEdit, 
                           QListWidget, QSplitter, QMessageBox)
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



class CubeGLWidget(QOpenGLWidget):
    """OpenGL widget that uses the CubeViz drawing methods"""
    
    def __init__(self, viz: CubeViz, parent=None):
        super(CubeGLWidget, self).__init__(parent)
        self.setMinimumSize(400, 400)

        self.viz = viz
        self.viz.attempt.listen_to(self.update)
        
        # Set up a timer for animation/updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30)  # 30ms refresh rate (approx 33 fps)
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.dragging = False

    def update_cube(self):
        """Update the cube based on the current solution builder"""
        self.viz.update()
        self.update()  # Trigger a repaint
        
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
        
        self.setWindowTitle("Cube Explorer")
        self.resize(1200, 800)
        
        self.attempt = Attempt()
        self.attempt.listen_to(self.refresh)

        self.history = []
        
        # Set up the OpenGL format
        gl_format = QSurfaceFormat()
        gl_format.setVersion(2, 1)
        gl_format.setProfile(QSurfaceFormat.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(gl_format)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
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
        self.step_label.setStyleSheet("background-color: #4d4d4d; color: white; font-weight: bold; font-size: 18px; padding: 5px;")
        self.step_label.setMinimumHeight(40)
        status_layout.addWidget(self.step_label, 1)  # Give it a stretch factor of 1
        
        # Right label - Case name
        self.case_label = QLabel("Case")
        self.case_label.setStyleSheet("background-color: #4d4d4d; color: white; font-weight: bold; font-size: 18px; padding: 5px;")
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

        # Command input below the GL widget
        command_container = QWidget()
        command_layout = QHBoxLayout(command_container)
        command_label = QLabel("Command:")
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.execute_command)
        execute_button = QPushButton("Execute")
        execute_button.clicked.connect(lambda: self.execute_command())
        
        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(execute_button)
        main_layout.addWidget(command_container)

        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        self.status_label = QLabel()
        status_layout.addWidget(self.status_label)
        main_layout.addWidget(status_container)
        
        # Solutions lists at the bottom
        solutions_container = QWidget()
        solutions_layout = QVBoxLayout(solutions_container)

        # Create a horizontal layout for the solution lists
        solution_lists_layout = QHBoxLayout()
        
        # EO solutions list
        eo_container = QWidget()
        eo_layout = QVBoxLayout(eo_container)
        eo_layout.addWidget(QLabel("EO:"))
        self.eo_solution_list = QListWidget()
        self.eo_solution_list.itemDoubleClicked.connect(self.check_solution)
        eo_layout.addWidget(self.eo_solution_list)
        solution_lists_layout.addWidget(eo_container)
        
        # DR solutions list
        dr_container = QWidget()
        dr_layout = QVBoxLayout(dr_container)
        dr_layout.addWidget(QLabel("DR:"))
        self.dr_solution_list = QListWidget()
        self.dr_solution_list.itemDoubleClicked.connect(self.check_solution)
        dr_layout.addWidget(self.dr_solution_list)
        solution_lists_layout.addWidget(dr_container)
        
        # HTR solutions list
        htr_container = QWidget()
        htr_layout = QVBoxLayout(htr_container)
        htr_layout.addWidget(QLabel("HTR:"))
        self.htr_solution_list = QListWidget()
        self.htr_solution_list.itemDoubleClicked.connect(self.check_solution)
        htr_layout.addWidget(self.htr_solution_list)
        solution_lists_layout.addWidget(htr_container)
        
        # FR solutions list
        fr_container = QWidget()
        fr_layout = QVBoxLayout(fr_container)
        fr_layout.addWidget(QLabel("FR:"))
        self.fr_solution_list = QListWidget()
        self.fr_solution_list.itemDoubleClicked.connect(self.check_solution)
        fr_layout.addWidget(self.fr_solution_list)
        solution_lists_layout.addWidget(fr_container)
        
        solutions_layout.addLayout(solution_lists_layout)
        main_layout.addWidget(solutions_container)
        
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
        solutions = self.attempt.saved_solutions()
        # EO solutions
        self.eo_solution_list.clear()
        for sol in solutions.get("eo", []):
                self.eo_solution_list.addItem(str(sol))

        # DR solutions
        self.dr_solution_list.clear()
        for sol in solutions.get("dr", []):
            self.dr_solution_list.addItem(str(sol))

        # HTR solutions
        self.htr_solution_list.clear()
        for sol in solutions.get("htr", []):
            self.htr_solution_list.addItem(str(sol))

        # FR solutions
        self.fr_solution_list.clear()
        for sol in solutions.get("fr", []):
            self.fr_solution_list.addItem(str(sol))


    def refresh(self):
        """Handle step changes"""
        # Update cube
        self.gl_widget.update_cube()
        
        # Update current solution
        self.refresh_current_solution()

        # Update solution lists
        self.refresh_saved_solutions()
        

    def set_scramble(self, scramble: str):
        """Set the cube to a specific scramble"""
        self.attempt.set_scramble(scramble)

    def generate_scramble(self):
        """Generate a random scramble"""
        scramble = gen_scramble()
        self.set_scramble(scramble)
        
    def execute_command(self):
        """Execute a command from the command input"""
        raw_command = self.command_input.text().strip()
        cmd = raw_command
        if not cmd:
            return
            
        try:
            # Check if it's a sequence of cube moves
            if all(m in MOVES for m in cmd.upper().split()):
                self._append_moves(cmd.upper())
            else:
                # Assume it's a Python command
                if cmd.find("(") < 0:
                    cmd = f"{cmd}()"
                # Use locals and globals from this context
                exec(f"self.{cmd}", globals(), {'self': self})
            self.history.append(raw_command)
        except NameError as e:
            self.status_label.setText(f"No such command: {raw_command}")
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(sys.exc_info())
            self.status_label.setText(f"Error: {str(e)}")
            
        self.command_input.clear()
    
    def _append_moves(self, moves):
        """Append moves to the current solution"""
        moves = moves.split(" ")
        inverse = self.attempt.inverse

        sol = self.attempt.solution
        
        if sol.alg.len() > 0:
            if not self.attempt.append_moves(moves, inverse):
                self.status_label.setText(
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
                    self.status_label.setText(
                        f"{moves} not allowed after {sol.previous.kind}{sol.previous.variant}")
        
    def eoud(self):
        """Look for EO on UD axis"""
        self._set_mode("eo", "ud")
        
    def eofb(self):
        """Look for EO on FB axis"""
        self._set_mode("eo", "fb")
        
    def eorl(self):
        """Look for EO on RL axis"""
        self._set_mode("eo", "rl")
        
    def drud(self):
        """Look for DR on UD axis"""
        self._set_mode("dr", "ud")
        
    def drfb(self):
        """Look for DR on FB axis"""
        self._set_mode("dr", "fb")
        
    def drrl(self):
        """Look for DR on RL axis"""
        self._set_mode("dr", "rl")
        
    def htr(self):
        """Look for HTR"""
        sol = self.attempt.solution
        self._set_mode("htr", sol.previous.variant if sol.previous else "ud")
        
    def fr(self):
        """Look for FR"""
        sol = self.attempt.solution
        self._set_mode("fr", sol.previous.variant if sol.previous else "ud")
        
    def niss(self):
        """Switch between normal and inverse scramble"""
        self.attempt.set_inverse(not self.attempt.inverse)

    def _set_mode(self, kind, variant) -> bool:
        """Change to a specific solving step"""
        step_info = StepInfo(kind, variant)
        sol = self.attempt.solution
        if step_info.is_eligible(self.attempt.cube):
            if (not sol.alg.is_empty()) and not sol.step_info.is_solved(self.attempt.cube):
                self.reset()
            self.attempt.advance_to(kind, variant)
            while step_info.is_solved(self.attempt.cube) and sol.previous:
                self.attempt.back()
            return True
        else:
            self.status_label.setText(f"Cube is not eligible for {kind}{variant}")
            return False
    
    def solve(self):
        """Find and save solutions for the current step"""
        sol = self.attempt.solution
        on_inverse = self.attempt.inverse
        if on_inverse:
            self.niss()
        n_existing = len(self.attempt.saved_solutions(sol.kind, sol.variant))
        if sol.alg.len() == 0:
            # Multiple solutions of the full step, auto-save
            self.status_label.setText(f"Finding solutions for {sol.kind}{sol.variant}...")
            algs = sol.step_info.solve(self.attempt.cube, n_existing + 10)
            self.status_label.setText(f"Found {len(algs)} solutions. Saving")
            count = 0
            for alg in algs:
                sol = PartialSolution(
                    kind=self.attempt.solution.kind,
                    variant=self.attempt.solution.variant,
                    alg=alg
                )
                count += 1 if self.attempt.save_solution(sol) else 0
                if count >= 10:
                    break
            self.list_solutions()
        else:
            algs = sol.step_info.solve(self.attempt.cube, n_existing + 1)
            if algs:
                existing = {f"{a}" for a in sol.saved_solutions_of_same_step()}
                for a in algs:
                    if f"{a}" not in existing:
                        sol.alg = sol.alg.merge(a)
                        self.attempt.set_solution(sol)
                        break
            else:
                self.status_label.setText("No solution found!")
        if on_inverse:
            self.niss()
    
    def save(self):
        """Save this algorithm and start a new one"""
        sol = self.attempt.solution
        if not sol.step_info.is_solved(self.attempt.cube):
            if sol.kind == "" or sol.previous is None:
                self.status_label.setText("Complete at least one step before saving")
                return
            partial = PartialSolution(
                kind=sol.previous.kind,
                variant=sol.previous.variant,
                previous=sol.previous.previous,
                alg=sol.previous.alg.merge(sol.alg),
            )
            options = NEXT_STEPS.get((partial.kind, partial.variant), [])
            case = sol.step_info.case_name(self.attempt.cube)
            partial.comment = f"{sol.kind}{sol.variant}-{case}" if len(options) > 1 else case
            self.attempt.save_solution(partial)
            return
        self.attempt.save()
        next_steps = NEXT_STEPS.get((sol.kind, sol.variant))
        if next_steps is not None and len(next_steps) == 1:
            self.attempt.advance_to(*next_steps[0])
        else:
            self.reset()
    
    def reset(self):
        """Reset the cube to the beginning of the current step"""
        self.attempt.reset()
    
    def back(self):
        """Go back to the previous step"""
        self.attempt.back()
    
    def check_solution(self, item):
        """Load a selected solution"""
        self.attempt.load(item.text())
        key = (self.attempt.solution.kind, self.attempt.solution.variant)
        next_steps = NEXT_STEPS.get(key)
        if next_steps:
            self.attempt.advance_to(*next_steps[0])


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

if __name__ == "__main__":
    main()