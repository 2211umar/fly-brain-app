import sys
import json
import math
import random

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QFrame,
    QCheckBox,
    QHeaderView,
    QDialog,
    QTextEdit,
    QMenu,
    QFileDialog,
    QSpinBox,
    QProgressBar,
    QSlider
)

from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QPoint
from PySide6.QtGui import (
    QDesktopServices,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont
)

import keyring

from neuprint import (
    Client,
    fetch_neurons,
    fetch_adjacencies,
    NeuronCriteria as NC
)


SERVER = "neuprint.janelia.org"
DATASET = "male-cns:v1.0"

KEYRING_SERVICE = "FruitFlyBrainExplorer"
KEYRING_USERNAME = "neuprint_api_token"


BRAIN_PARTS = {
    "Mushroom Body (Memory & Learning)": {
        "search": "MBON",
        "description": "The Mushroom Body is strongly involved in learning, memory and processing information about experiences."
    },
    "Kenyon Cells (Memory Cells)": {
        "search": "KC",
        "description": "Kenyon Cells are major neurons of the Mushroom Body and process sensory information."
    },
    "Descending Neurons (Movement)": {
        "search": "DNge",
        "description": "Descending Neurons send information from the brain toward motor systems involved in movement."
    },
    "Visual Neurons (Vision)": {
        "search": "LC",
        "description": "Visual neurons process information received from the fly's visual system."
    },
    "Ellipsoid Ring (Movement & Direction)": {
        "search": "ER",
        "description": "The Ellipsoid Ring is associated with the central complex and neural processing."
    },
    "Antennal Lobe (Smell)": {
        "search": "AL",
        "description": "The Antennal Lobe is a major smell-processing region that receives information from the fly's antennae."
    },
    "Fan-Shaped Body (Navigation)": {
        "search": "FB",
        "description": "The Fan-Shaped Body is part of the central complex and is involved in navigation and behavioural processing."
    },
    "Ellipsoid Body (Direction)": {
        "search": "EB",
        "description": "The Ellipsoid Body is part of the central complex and contributes to spatial and directional processing."
    },
    "Lateral Horn (Smell & Behaviour)": {
        "search": "LH",
        "description": "The Lateral Horn is involved in processing smell information and behavioural responses."
    },
    "Central Complex (Navigation & Movement)": {
        "search": "CX",
        "description": "The Central Complex is a collection of brain regions involved in navigation, orientation and behavioural control."
    }
}


FRUIT_TYPES = {
    "Apple": {
        "taste": "SWEET",
        "reward": 10,
        "smell": 60
    },
    "Banana": {
        "taste": "SWEET",
        "reward": 8,
        "smell": 70
    },
    "Orange": {
        "taste": "CITRUS",
        "reward": 12,
        "smell": 80
    },
    "Strawberry": {
        "taste": "SWEET",
        "reward": 15,
        "smell": 90
    },
    "Grape": {
        "taste": "SWEET",
        "reward": 9,
        "smell": 55
    }
}


SAND_FRUIT_EMOJI = {
    "Apple": "🍎",
    "Banana": "🍌",
    "Orange": "🍊",
    "Strawberry": "🍓",
    "Grape": "🍇"
}


class SandboxCanvas(QWidget):

    state_changed = Signal()

    def __init__(self):
        super().__init__()

        self.setMinimumSize(700, 500)
        self.setMouseTracking(True)

        self.running = False
        self.speed_multiplier = 1.0

        self.fly_x = 350.0
        self.fly_y = 250.0
        self.fly_angle = 0.0
        self.fly_speed = 2.2

        self.foods = []
        self.obstacles = []

        self.food_collected = 0
        self.total_reward = 0

        self.memories = {}

        self.vision_range = 190.0
        self.vision_angle = math.radians(75)
        self.smell_range = 155.0

        self.vision_activity = 0.0
        self.smell_activity = 0.0
        self.taste_activity = 0.0

        self.brain_activity = {
            "Antennal Lobe": 0.0,
            "Visual Neurons": 0.0,
            "Kenyon Cells": 0.0,
            "Mushroom Body": 0.0,
            "Central Complex": 0.0,
            "Descending Neurons": 0.0
        }

        self.mouse_x = 0
        self.mouse_y = 0

        self.dragging = None

        self.hover_obstacle = None

        self.hover_food = None

        self.setFocusPolicy(
            Qt.StrongFocus
        )

        self.selected_fruit_type = "Apple"

        self.fruit_types = FRUIT_TYPES

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)

        self.reset_world()

    def reset_world(self):

        self.fly_x = max(100, self.width() / 2)
        self.fly_y = max(100, self.height() / 2)
        self.fly_angle = random.uniform(0, math.pi * 2)

        self.foods = [
            {
                "x": self.fly_x + 170,
                "y": self.fly_y - 100,
                "type": "Apple",
                "taste": "SWEET",
                "reward": 10,
                "smell": 60,
                "rot": False,
                "rot_timer": 2700
            },
            {
                "x": self.fly_x - 220,
                "y": self.fly_y + 100,
                "type": "Banana",
                "taste": "SWEET",
                "reward": 8,
                "smell": 70,
                "rot": False,
                "rot_timer": 2700
            }
        ]

        self.obstacles = [
            {
                "x": self.fly_x - 50,
                "y": self.fly_y - 170,
                "w": 110,
                "h": 25
            },
            {
                "x": self.fly_x + 100,
                "y": self.fly_y + 100,
                "w": 130,
                "h": 25
            }
        ]

        self.food_collected = 0
        self.total_reward = 0
        self.memories = {}

        self.vision_activity = 0
        self.smell_activity = 0
        self.taste_activity = 0

        for key in self.brain_activity:
            self.brain_activity[key] = 0

        self.state_changed.emit()
        self.update()

    def start(self):

        self.running = True

        if not self.timer.isActive():
            self.timer.start(30)

        self.state_changed.emit()

    def pause(self):

        self.running = False
        self.timer.stop()
        self.state_changed.emit()

    def reset(self):

        self.pause()
        self.reset_world()

    def set_speed(self, value):

        self.speed_multiplier = float(value)

    def add_fruit(
        self,
        fruit_type,
        x=None,
        y=None
    ):

        fruit = self.fruit_types[fruit_type]

        if x is None:

            margin = 70

            width = max(self.width(), 800)
            height = max(self.height(), 500)

            x = random.uniform(
                margin,
                width - margin
            )

            y = random.uniform(
                margin,
                height - margin
            )

        self.foods.append(
            {
                "x": float(x),
                "y": float(y),
                "type": fruit_type,
                "taste": fruit["taste"],
                "reward": fruit["reward"],
                "smell": fruit["smell"],
                "rot": False,
                "rot_timer": self.fresh_rot_timer()
            }
        )

        self.state_changed.emit()
        self.update()

    def add_obstacle(self, x=None, y=None):

        if x is None:
            margin = 100

            width = max(self.width(), 800)
            height = max(self.height(), 500)

            x = random.uniform(
                margin,
                width - margin - 120
            )

            y = random.uniform(
                margin,
                height - margin - 35
            )

        self.obstacles.append(
            {
                "x": float(x),
                "y": float(y),
                "w": 120,
                "h": 35
            }
        )

        self.state_changed.emit()
        self.update()

    def mouseMoveEvent(self, event):

        self.mouse_x = event.position().x()
        self.mouse_y = event.position().y()

        if self.dragging:

            kind = self.dragging["kind"]

            if kind == "resize":

                self.resize_obstacle_to(
                    self.dragging["object"],
                    self.dragging["edges"],
                    self.mouse_x,
                    self.mouse_y
                )

                self.update()
                return

            offset_x = self.dragging["offset_x"]
            offset_y = self.dragging["offset_y"]

            if kind == "fly":

                width = max(self.width(), 700)
                height = max(self.height(), 500)

                self.fly_x = min(
                    max(120, self.mouse_x - offset_x),
                    width - 120
                )

                self.fly_y = min(
                    max(90, self.mouse_y - offset_y),
                    height - 90
                )

            else:

                object_data = self.dragging["object"]

                width = max(self.width(), 700)
                height = max(self.height(), 500)

                obstacle_width = object_data.get("w", 0)
                obstacle_height = object_data.get("h", 0)

                object_data["x"] = min(
                    max(40, self.mouse_x - offset_x),
                    width - 40 - obstacle_width
                )

                object_data["y"] = min(
                    max(40, self.mouse_y - offset_y),
                    height - 40 - obstacle_height
                )

            self.update()
            return

        hovered = self.hover_obstacle or self.hover_food

        hit_kind, hit_object = self.hit_test(
            self.mouse_x,
            self.mouse_y
        )

        self.hover_obstacle = (
            hit_object
            if hit_kind == "obstacle"
            else None
        )

        self.hover_food = (
            hit_object
            if hit_kind == "food"
            else None
        )

        if (
            (self.hover_obstacle or self.hover_food)
            is not hovered
        ):

            self.update()

    def mousePressEvent(self, event):

        x = event.position().x()
        y = event.position().y()

        self.setFocus()

        if event.button() == Qt.RightButton:

            self.open_context_menu(x, y)
            return

        if event.button() == Qt.LeftButton:

            kind = None
            object_data = None

            if self.distance(
                x,
                y,
                self.fly_x,
                self.fly_y
            ) < 28:

                kind = "fly"

            else:

                kind, object_data = self.hit_test(x, y)

            if kind == "fly":

                previous = self.running

                self.pause()

                self.dragging = {
                    "kind": "fly",
                    "previous": previous,
                    "offset_x": x - self.fly_x,
                    "offset_y": y - self.fly_y
                }

            elif kind == "food":

                previous = self.running

                self.pause()

                self.dragging = {
                    "kind": "food",
                    "previous": previous,
                    "object": object_data,
                    "offset_x": x - object_data["x"],
                    "offset_y": y - object_data["y"]
                }

            elif kind == "obstacle":

                previous = self.running

                self.pause()

                edges = self.obstacle_edge_hit(
                    x,
                    y,
                    object_data
                )

                if edges:

                    self.dragging = {
                        "kind": "resize",
                        "previous": previous,
                        "object": object_data,
                        "edges": edges
                    }

                else:

                    self.dragging = {
                        "kind": "obstacle",
                        "previous": previous,
                        "object": object_data,
                        "offset_x": x - object_data["x"],
                        "offset_y": y - object_data["y"]
                    }

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.drag_end()

    def drag_end(self):

        if self.dragging:

            previous = self.dragging["previous"]

            self.dragging = None

            self.running = previous

            self.state_changed.emit()
            self.update()

            if previous:

                if not self.timer.isActive():
                    self.timer.start(30)

    def hit_test(self, x, y):

        for food in self.foods:

            if self.distance(
                x,
                y,
                food["x"],
                food["y"]
            ) < 26:

                return ("food", food)

        for obstacle in self.obstacles:

            if (
                obstacle["x"] <= x <= obstacle["x"] + obstacle["w"]
                and
                obstacle["y"] <= y <= obstacle["y"] + obstacle["h"]
            ):

                return ("obstacle", obstacle)

        return (None, None)

    def keyPressEvent(self, event):

        key = event.key()

        if key == Qt.Key_Space:

            if self.running:

                self.pause()

            else:

                self.start()

            return

        if key == Qt.Key_Delete or key == Qt.Key_Backspace:

            self.delete_hovered()
            return

        if key == Qt.Key_R:

            if event.modifiers() & Qt.ControlModifier:

                self.reset()
                return

            self.rotate_hovered()
            return

        if key == Qt.Key_D:

            self.duplicate_hovered()
            return

        if key == Qt.Key_M:

            self.toggle_rotten_hovered()
            return

        if Qt.Key_1 <= key <= Qt.Key_5:

            index = key - Qt.Key_1

            fruit_type = list(
                FRUIT_TYPES.keys()
            )[index]

            self.set_hovered_food_type(fruit_type)
            return

        if key == Qt.Key_L:

            self.resize_hovered("longer")
            return

        if key == Qt.Key_T:

            self.resize_hovered("thicker")
            return

        if key == Qt.Key_N:

            self.resize_hovered("thinner")
            return

        if key == Qt.Key_A:

            self.add_fruit(
                self.selected_fruit_type
            )
            return

        if key == Qt.Key_O:

            self.add_obstacle()
            return

        super().keyPressEvent(event)

    def delete_hovered(self):

        if self.hover_food:

            self.delete_food(self.hover_food)

        elif self.hover_obstacle:

            self.delete_obstacle(self.hover_obstacle)

    def duplicate_hovered(self):

        if self.hover_food:

            self.duplicate_food(self.hover_food)

        elif self.hover_obstacle:

            self.duplicate_obstacle(self.hover_obstacle)

    def rotate_hovered(self):

        if self.hover_obstacle:

            self.rotate_obstacle(self.hover_obstacle)

        elif self.hover_food is None:

            self.rotate_fly()

    def toggle_rotten_hovered(self):

        if self.hover_food:

            self.set_food_rotten(
                self.hover_food,
                not self.hover_food.get("rot")
            )

    def set_hovered_food_type(self, fruit_type):

        if self.hover_food:

            self.set_fruit_type(
                self.hover_food,
                fruit_type
            )

    def resize_hovered(self, action):

        if self.hover_obstacle:

            self.resize_obstacle(
                self.hover_obstacle,
                action
            )

    def open_context_menu(self, x, y):

        menu = self.build_context_menu(x, y)

        if menu.actions():

            menu.exec(
                self.mapToGlobal(
                    QPoint(
                        int(x),
                        int(y)
                    )
                )
            )

    def build_context_menu(self, x, y):

        menu = QMenu(self)

        if self.distance(
            x,
            y,
            self.fly_x,
            self.fly_y
        ) < 28:

            rotate_fly = menu.addAction(
                "⟳ Rotate fly  (R)"
            )

            rotate_fly.triggered.connect(
                self.rotate_fly
            )

        else:

            kind, object_data = self.hit_test(x, y)

            if kind == "food":

                food = object_data

                change_menu = menu.addMenu(
                    "Change type"
                )

                current_type = food["type"]

                for index, fruit_type in enumerate(
                    FRUIT_TYPES
                ):

                    action = change_menu.addAction(
                        SAND_FRUIT_EMOJI[fruit_type]
                        +
                        " "
                        +
                        fruit_type
                        +
                        "  ("
                        +
                        str(index + 1)
                        +
                        ")"
                    )

                    action.setCheckable(
                        True
                    )

                    action.setChecked(
                        fruit_type == current_type
                    )

                    action.triggered.connect(
                        lambda
                        checked=False,
                        f=food,
                        t=fruit_type:
                        self.set_fruit_type(
                            f,
                            t
                        )
                    )

                duplicate_food = menu.addAction(
                    "📑 Duplicate  (D)"
                )

                duplicate_food.triggered.connect(
                    lambda
                    checked=False,
                    f=food:
                    self.duplicate_food(f)
                )

                if food.get("rot"):

                    make_fresh = menu.addAction(
                        "✨ Make fresh  (M)"
                    )

                    make_fresh.triggered.connect(
                        lambda
                        checked=False,
                        f=food:
                        self.set_food_rotten(f, False)
                    )

                else:

                    make_rotten = menu.addAction(
                        "🥀 Make rotten  (M)"
                    )

                    make_rotten.triggered.connect(
                        lambda
                        checked=False,
                        f=food:
                        self.set_food_rotten(f, True)
                    )

                delete_food = menu.addAction(
                    "🗑️ Delete  (Del)"
                )

                delete_food.triggered.connect(
                    lambda
                    checked=False,
                    f=food:
                    self.delete_food(f)
                )

            elif kind == "obstacle":

                obstacle = object_data

                rotate = menu.addAction(
                    "⟳ Rotate  (R)"
                )

                rotate.triggered.connect(
                    lambda
                    checked=False,
                    o=obstacle:
                    self.rotate_obstacle(o)
                )

                longer = menu.addAction(
                    "Make longer  (L)"
                )

                longer.triggered.connect(
                    lambda
                    checked=False,
                    o=obstacle:
                    self.resize_obstacle(
                        o,
                        "longer"
                    )
                )

                thicker = menu.addAction(
                    "Make thicker  (T)"
                )

                thicker.triggered.connect(
                    lambda
                    checked=False,
                    o=obstacle:
                    self.resize_obstacle(
                        o,
                        "thicker"
                    )
                )

                thinner = menu.addAction(
                    "Make thinner  (N)"
                )

                thinner.triggered.connect(
                    lambda
                    checked=False,
                    o=obstacle:
                    self.resize_obstacle(
                        o,
                        "thinner"
                    )
                )

                duplicate_obstacle = menu.addAction(
                    "📑 Duplicate  (D)"
                )

                duplicate_obstacle.triggered.connect(
                    lambda
                    checked=False,
                    o=obstacle:
                    self.duplicate_obstacle(o)
                )

                delete_obstacle = menu.addAction(
                    "🗑️ Delete  (Del)"
                )

                delete_obstacle.triggered.connect(
                    lambda
                    checked=False,
                    o=obstacle:
                    self.delete_obstacle(o)
                )

        return menu

    def set_fruit_type(
        self,
        food,
        fruit_type
    ):

        food["type"] = fruit_type

        self.refresh_food_stats(food)

        self.state_changed.emit()
        self.update()

    def refresh_food_stats(self, food):

        fruit = self.fruit_types[
            food["type"]
        ]

        if food.get("rot"):

            food["taste"] = "NASTY"
            food["reward"] = -abs(
                fruit["reward"]
            )

        else:

            food["taste"] = fruit["taste"]
            food["reward"] = fruit["reward"]

        food["smell"] = fruit["smell"]

    def delete_food(self, food):

        if food in self.foods:

            self.foods.remove(food)

            if self.hover_food is food:
                self.hover_food = None

        self.state_changed.emit()
        self.update()

    def delete_obstacle(self, obstacle):

        if obstacle in self.obstacles:

            self.obstacles.remove(obstacle)

            if self.hover_obstacle is obstacle:
                self.hover_obstacle = None

        self.state_changed.emit()
        self.update()

    def rotate_obstacle(self, obstacle):

        obstacle["w"], obstacle["h"] = (
            obstacle["h"],
            obstacle["w"]
        )

        self.state_changed.emit()
        self.update()

    def resize_obstacle(
        self,
        obstacle,
        action
    ):

        if action == "longer":

            obstacle["w"] = max(
                40,
                obstacle["w"] + 40
            )

        elif action == "thicker":

            obstacle["h"] = max(
                20,
                obstacle["h"] + 20
            )

        elif action == "thinner":

            obstacle["h"] = max(
                20,
                obstacle["h"] - 20
            )

        self.state_changed.emit()
        self.update()

    def obstacle_edge_hit(
        self,
        x,
        y,
        obstacle,
        pad=8
    ):

        left = obstacle["x"]
        top = obstacle["y"]
        right = left + obstacle["w"]
        bottom = top + obstacle["h"]

        edges = []

        if (
            abs(x - left) <= pad
            and
            top - 6 <= y <= bottom + 6
        ):

            edges.append("left")

        if (
            abs(x - right) <= pad
            and
            top - 6 <= y <= bottom + 6
        ):

            edges.append("right")

        if (
            abs(y - top) <= pad
            and
            left - 6 <= x <= right + 6
        ):

            edges.append("top")

        if (
            abs(y - bottom) <= pad
            and
            left - 6 <= x <= right + 6
        ):

            edges.append("bottom")

        return edges

    def resize_obstacle_to(
        self,
        obstacle,
        edges,
        mouse_x,
        mouse_y
    ):

        min_w = 30
        min_h = 20

        left = obstacle["x"]
        top = obstacle["y"]
        right = left + obstacle["w"]
        bottom = top + obstacle["h"]

        if "left" in edges:

            new_left = max(
                40,
                min(
                    mouse_x,
                    right - min_w
                )
            )

            obstacle["x"] = new_left
            obstacle["w"] = right - new_left

        elif "right" in edges:

            new_right = max(
                left + min_w,
                min(
                    mouse_x,
                    self.width() - 40
                )
            )

            obstacle["w"] = new_right - left

        if "top" in edges:

            new_top = max(
                40,
                min(
                    mouse_y,
                    bottom - min_h
                )
            )

            obstacle["y"] = new_top
            obstacle["h"] = bottom - new_top

        elif "bottom" in edges:

            new_bottom = max(
                top + min_h,
                min(
                    mouse_y,
                    self.height() - 40
                )
            )

            obstacle["h"] = new_bottom - top

    def fresh_rot_timer(self):

        return int(
            random.uniform(15, 45) * 30
        )

    def duplicate_food(self, food):

        new_food = dict(food)

        new_food["x"] = min(
            max(self.width(), 700) - 40,
            food["x"] + 30
        )

        new_food["y"] = min(
            max(self.height(), 500) - 40,
            food["y"] + 30
        )

        new_food["rot"] = False
        new_food["rot_timer"] = self.fresh_rot_timer()

        self.refresh_food_stats(new_food)

        self.foods.append(new_food)

        self.state_changed.emit()
        self.update()

    def duplicate_obstacle(self, obstacle):

        new_obstacle = dict(obstacle)

        new_obstacle["x"] = min(
            max(self.width(), 700) - 40 - obstacle["w"],
            obstacle["x"] + 30
        )

        new_obstacle["y"] = min(
            max(self.height(), 500) - 40 - obstacle["h"],
            obstacle["y"] + 30
        )

        self.obstacles.append(new_obstacle)

        self.state_changed.emit()
        self.update()

    def set_food_rotten(
        self,
        food,
        rotten
    ):

        food["rot"] = rotten

        if rotten:

            food["rot_timer"] = 0

        self.refresh_food_stats(food)

        self.state_changed.emit()
        self.update()

    def rotate_fly(self):

        self.fly_angle = (
            self.fly_angle
            +
            math.radians(45)
        ) % (
            math.pi * 2
        )

        self.state_changed.emit()
        self.update()

    def distance(self, x1, y1, x2, y2):

        return math.sqrt(
            (x2 - x1) ** 2 +
            (y2 - y1) ** 2
        )

    def angle_difference(self, a, b):

        difference = (
            b - a + math.pi
        ) % (
            math.pi * 2
        ) - math.pi

        return difference

    def is_in_vision(self, food):

        dx = food["x"] - self.fly_x
        dy = food["y"] - self.fly_y

        distance = math.sqrt(
            dx * dx +
            dy * dy
        )

        if distance > self.vision_range:
            return False

        target_angle = math.atan2(
            dy,
            dx
        )

        difference = abs(
            self.angle_difference(
                self.fly_angle,
                target_angle
            )
        )

        return difference <= self.vision_angle / 2

    def calculate_senses(self):

        visible_foods = []

        for food in self.foods:

            in_range = (
                self.distance(
                    self.fly_x,
                    self.fly_y,
                    food["x"],
                    food["y"]
                )
                <= food.get("smell", 60)
            )

            if (
                in_range
                and
                self.is_in_vision(food)
            ):

                visible_foods.append(
                    food
                )

        if visible_foods:

            nearest_visible = min(
                visible_foods,
                key=lambda item:
                (
                    item["reward"],
                    -self.distance(
                        self.fly_x,
                        self.fly_y,
                        item["x"],
                        item["y"]
                    )
                )
            )

            distance = self.distance(
                self.fly_x,
                self.fly_y,
                nearest_visible["x"],
                nearest_visible["y"]
            )

            self.vision_activity = max(
                0,
                1 - distance / self.vision_range
            )

        else:

            self.vision_activity *= 0.92

        smell_targets = []

        for food in self.foods:

            smell_range = food.get("smell", 60)

            distance = self.distance(
                self.fly_x,
                self.fly_y,
                food["x"],
                food["y"]
            )

            if distance <= smell_range:

                smell_targets.append(
                    food
                )

        if smell_targets:

            closest_smell = min(
                smell_targets,
                key=lambda item: self.distance(
                    self.fly_x,
                    self.fly_y,
                    item["x"],
                    item["y"]
                )
            )

            smell_distance = self.distance(
                self.fly_x,
                self.fly_y,
                closest_smell["x"],
                closest_smell["y"]
            )

            self.smell_activity = max(
                0,
                1 - smell_distance / self.smell_range
            )

        else:

            self.smell_activity *= 0.94

        self.taste_activity *= 0.90

        self.brain_activity[
            "Antennal Lobe"
        ] = self.smell_activity

        self.brain_activity[
            "Visual Neurons"
        ] = self.vision_activity

        self.brain_activity[
            "Kenyon Cells"
        ] = min(
            1,
            (
                self.smell_activity * 0.5
                +
                self.vision_activity * 0.5
            )
        )

        memory_activity = 0

        if self.memories:

            memory_activity = min(
                1,
                0.25 +
                len(self.memories) * 0.12
            )

        self.brain_activity[
            "Mushroom Body"
        ] = max(
            memory_activity,
            self.taste_activity
        )

        navigation = max(
            self.vision_activity,
            self.smell_activity
        )

        self.brain_activity[
            "Central Complex"
        ] = navigation

        self.brain_activity[
            "Descending Neurons"
        ] = min(
            1,
            self.fly_speed / 4.0
        )

    def food_memory_key(self, food):

        return (
            food["type"]
            +
            ":"
            +
            food.get(
                "taste",
                "SWEET"
            )
        )

    def food_preference(self, food):

        memory = self.memories.get(
            self.food_memory_key(food)
        )

        if (
            memory
            and
            memory.get("seen")
        ):

            return (
                memory["reward"]
                /
                memory["seen"]
            )

        return 0.0

    def find_target(self):

        if not self.foods:
            return None

        def score(item):

            return (
                self.distance(
                    self.fly_x,
                    self.fly_y,
                    item["x"],
                    item["y"]
                )
                -
                self.food_preference(item) * 3
            )

        visible = [
            food for food in self.foods
            if (
                self.is_in_vision(food)
                and
                self.food_preference(food) > -1
            )
        ]

        if visible:

            return min(
                visible,
                key=score
            )

        smell_targets = [
            food for food in self.foods
            if (
                self.distance(
                    self.fly_x,
                    self.fly_y,
                    food["x"],
                    food["y"]
                )
                <= self.smell_range
                and
                self.food_preference(food) > -1
            )
        ]

        if smell_targets:

            return min(
                smell_targets,
                key=score
            )

        if self.memories:

            remembered = [
                food for food in self.foods
                if (
                    self.memories.get(
                        self.food_memory_key(food)
                    )
                    and
                    self.food_preference(food) > -1
                )
            ]

            if remembered:

                return min(
                    remembered,
                    key=score
                )

        return None

    def find_repellent(self):

        if not self.memories:
            return None

        repellents = []

        for food in self.foods:

            preference = self.food_preference(food)

            if preference > -1:
                continue

            distance = self.distance(
                self.fly_x,
                self.fly_y,
                food["x"],
                food["y"]
            )

            if distance <= self.smell_range:

                repellents.append(
                    (food, distance, -preference)
                )

        if not repellents:
            return None

        repellents.sort(
            key=lambda item:
            item[1] - item[2] * 2
        )

        return repellents[0][0]

    def check_obstacle(self, new_x, new_y):

        fly_radius = 10

        for obstacle in self.obstacles:

            left = obstacle["x"] - fly_radius
            right = (
                obstacle["x"]
                +
                obstacle["w"]
                +
                fly_radius
            )

            top = obstacle["y"] - fly_radius
            bottom = (
                obstacle["y"]
                +
                obstacle["h"]
                +
                fly_radius
            )

            if (
                left <= new_x <= right
                and
                top <= new_y <= bottom
            ):

                return True

        return False

    def move_fly(self):

        target = self.find_target()

        repellent = self.find_repellent()

        desired_angle = self.fly_angle

        if repellent:

            repel_angle = math.atan2(
                self.fly_y - repellent["y"],
                self.fly_x - repellent["x"]
            )

            if target:

                target_angle = math.atan2(
                    target["y"] - self.fly_y,
                    target["x"] - self.fly_x
                )

                avoid_diff = self.angle_difference(
                    repel_angle,
                    target_angle
                )

                repel_strength = min(
                    1,
                    (
                        self.smell_range
                        /
                        max(
                            20,
                            self.distance(
                                self.fly_x,
                                self.fly_y,
                                repellent["x"],
                                repellent["y"]
                            )
                        )
                    )
                    *
                    0.5
                )

                desired_angle = (
                    repel_angle
                    +
                    avoid_diff * (1 - repel_strength)
                )

            else:

                desired_angle = (
                    repel_angle
                    +
                    random.uniform(
                        -0.2,
                        0.2
                    )
                )

        elif target:

            desired_angle = math.atan2(
                target["y"] - self.fly_y,
                target["x"] - self.fly_x
            )

        else:

            desired_angle += random.uniform(
                -0.08,
                0.08
            )

        turn = self.angle_difference(
            self.fly_angle,
            desired_angle
        )

        max_turn = 0.07 * self.speed_multiplier

        if repellent:

            max_turn = 0.35 * self.speed_multiplier

        turn = max(
            -max_turn,
            min(
                max_turn,
                turn
            )
        )

        self.fly_angle += turn

        movement_speed = (
            self.fly_speed
            *
            self.speed_multiplier
        )

        new_x = (
            self.fly_x
            +
            math.cos(self.fly_angle)
            *
            movement_speed
        )

        new_y = (
            self.fly_y
            +
            math.sin(self.fly_angle)
            *
            movement_speed
        )

        margin = 20

        width = max(
            self.width(),
            700
        )

        height = max(
            self.height(),
            500
        )

        if (
            new_x < margin
            or
            new_x > width - margin
            or
            new_y < margin
            or
            new_y > height - margin
        ):

            self.fly_angle += math.pi * 0.65

            new_x = (
                self.fly_x
                +
                math.cos(self.fly_angle)
                *
                movement_speed
            )

            new_y = (
                self.fly_y
                +
                math.sin(self.fly_angle)
                *
                movement_speed
            )

        if self.check_obstacle(
            new_x,
            new_y
        ):

            self.fly_angle += math.pi * 0.7

        else:

            self.fly_x = new_x
            self.fly_y = new_y

    def check_food(self):

        eaten = []

        for food in self.foods:

            distance = self.distance(
                self.fly_x,
                self.fly_y,
                food["x"],
                food["y"]
            )

            if distance < 18:

                eaten.append(food)

        for food in eaten:

            self.foods.remove(food)

            self.food_collected += 1

            self.total_reward += food["reward"]

            self.taste_activity = 1.0

            food_type = food["type"]
            taste = food["taste"]
            reward = food["reward"]

            state = "ROTTEN" if food.get("rot") else "FRESH"

            memory_key = (
                food_type
                +
                ":"
                +
                taste
            )

            if memory_key not in self.memories:

                self.memories[
                    memory_key
                ] = {
                    "type": food_type,
                    "taste": taste,
                    "reward": reward,
                    "seen": 1,
                    "state": state
                }

            else:

                self.memories[
                    memory_key
                ]["seen"] += 1

                self.memories[
                    memory_key
                ]["reward"] = (
                    self.memories[
                        memory_key
                    ]["reward"]
                    +
                    reward
                )

            self.add_fruit(
                random.choice(
                    list(FRUIT_TYPES.keys())
                )
            )

    def update_simulation(self):

        if not self.running:
            return

        for food in self.foods:

            if not food.get("rot"):

                food["rot_timer"] = food.get(
                    "rot_timer",
                    900
                ) - 1

                if food["rot_timer"] <= 0:

                    food["rot"] = True

                    self.refresh_food_stats(food)

        self.calculate_senses()
        self.move_fly()
        self.check_food()
        self.calculate_senses()

        self.state_changed.emit()
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        width = self.width()
        height = self.height()

        painter.fillRect(
            0,
            0,
            width,
            height,
            QColor("#0d1118")
        )

        grid_pen = QPen(
            QColor("#1c2633")
        )

        grid_pen.setWidth(1)

        painter.setPen(
            grid_pen
        )

        grid_size = 40

        for x in range(
            0,
            width,
            grid_size
        ):

            painter.drawLine(
                x,
                0,
                x,
                height
            )

        for y in range(
            0,
            height,
            grid_size
        ):

            painter.drawLine(
                0,
                y,
                width,
                y
            )

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QColor(40, 90, 150, 28)
        )

        painter.drawEllipse(
            int(
                self.fly_x
                -
                self.vision_range
            ),
            int(
                self.fly_y
                -
                self.vision_range
            ),
            int(
                self.vision_range * 2
            ),
            int(
                self.vision_range * 2
            )
        )

        for food in self.foods:

            if food.get("rot"):

                painter.setBrush(
                    QColor(120, 110, 90, 34)
                )

                painter.drawEllipse(
                    int(
                        food["x"]
                        -
                        self.smell_range
                    ),
                    int(
                        food["y"]
                        -
                        self.smell_range
                    ),
                    int(
                        self.smell_range * 2
                    ),
                    int(
                        self.smell_range * 2
                    )
                )

                continue

            smell_distance = self.distance(
                self.fly_x,
                self.fly_y,
                food["x"],
                food["y"]
            )

            smell_alpha = 28

            if smell_distance < self.smell_range:

                smell_alpha = 45

            painter.setBrush(
                QColor(
                    255,
                    130,
                    60,
                    smell_alpha
                )
            )

            painter.drawEllipse(
                int(
                    food["x"]
                    -
                    self.smell_range
                ),
                int(
                    food["y"]
                    -
                    self.smell_range
                ),
                int(
                    self.smell_range * 2
                ),
                int(
                    self.smell_range * 2
                )
            )

        for obstacle in self.obstacles:

            painter.setBrush(
                QColor("#555c6e")
            )

            painter.setPen(
                QPen(
                    QColor("#747d91"),
                    2
                )
            )

            painter.drawRoundedRect(
                int(obstacle["x"]),
                int(obstacle["y"]),
                int(obstacle["w"]),
                int(obstacle["h"]),
                7,
                7
            )

            painter.setPen(
                QColor("#c6cad3")
            )

            painter.setFont(
                QFont(
                    "Segoe UI",
                    9
                )
            )

            painter.drawText(
                int(obstacle["x"]),
                int(obstacle["y"] - 7),
                "Obstacle"
            )

            show_handles = (
                obstacle is self.hover_obstacle
                or
                (
                    self.dragging
                    and
                    self.dragging.get("object") is obstacle
                )
            )

            if show_handles:

                painter.setPen(
                    Qt.NoPen
                )

                painter.setBrush(
                    QColor("#9fd6ff")
                )

                handle = 7

                points = [
                    (
                        obstacle["x"] + obstacle["w"] / 2,
                        obstacle["y"]
                    ),
                    (
                        obstacle["x"] + obstacle["w"] / 2,
                        obstacle["y"] + obstacle["h"]
                    ),
                    (
                        obstacle["x"],
                        obstacle["y"] + obstacle["h"] / 2
                    ),
                    (
                        obstacle["x"] + obstacle["w"],
                        obstacle["y"] + obstacle["h"] / 2
                    ),
                    (
                        obstacle["x"],
                        obstacle["y"]
                    ),
                    (
                        obstacle["x"] + obstacle["w"],
                        obstacle["y"]
                    ),
                    (
                        obstacle["x"],
                        obstacle["y"] + obstacle["h"]
                    ),
                    (
                        obstacle["x"] + obstacle["w"],
                        obstacle["y"] + obstacle["h"]
                    )
                ]

                for px, py in points:

                    painter.drawRect(
                        int(px - handle / 2),
                        int(py - handle / 2),
                        handle,
                        handle
                    )

        painter.setPen(
            Qt.NoPen
        )

        for food in self.foods:

            if food.get("rot"):

                painter.setPen(
                    Qt.NoPen
                )

                food_type = food["type"]

                if food_type == "Banana":

                    painter.setBrush(
                        QColor("#6e6149")
                    )

                    painter.drawChord(
                        int(food["x"] - 18),
                        int(food["y"] - 10),
                        36,
                        24,
                        0,
                        180 * 16
                    )

                    painter.setPen(
                        QPen(
                            QColor("#3a3326"),
                            2
                        )
                    )

                    painter.drawLine(
                        int(food["x"] - 18),
                        int(food["y"]),
                        int(food["x"] - 25),
                        int(food["y"] - 6)
                    )

                    painter.setPen(
                        Qt.NoPen
                    )

                    painter.setBrush(
                        QColor("#4d4a35")
                    )

                    painter.drawEllipse(
                        int(food["x"] - 8),
                        int(food["y"] - 6),
                        6,
                        5
                    )

                elif food_type == "Orange":

                    painter.setBrush(
                        QColor("#9a7a4a")
                    )

                    painter.drawEllipse(
                        int(food["x"] - 15),
                        int(food["y"] - 15),
                        30,
                        30
                    )

                    painter.setBrush(
                        QColor("#5f6840")
                    )

                    painter.drawEllipse(
                        int(food["x"] - 10),
                        int(food["y"] - 12),
                        8,
                        8
                    )

                    painter.drawEllipse(
                        int(food["x"] + 4),
                        int(food["y"] + 2),
                        7,
                        7
                    )

                elif food_type == "Strawberry":

                    painter.setBrush(
                        QColor("#9a4a38")
                    )

                    painter.drawEllipse(
                        int(food["x"] - 12),
                        int(food["y"] - 8),
                        24,
                        27
                    )

                    painter.setBrush(
                        QColor("#5f6142")
                    )

                    painter.drawEllipse(
                        int(food["x"] - 8),
                        int(food["y"] - 4),
                        6,
                        5
                    )

                    painter.drawEllipse(
                        int(food["x"] + 4),
                        int(food["y"] + 3),
                        5,
                        5
                    )

                elif food_type == "Grape":

                    colors = [
                        "#7a6a55",
                        "#6b5c49",
                        "#5f5340",
                        "#8a7a62"
                    ]

                    offsets = [
                        (-9, -6),
                        (3, -6),
                        (-3, 3),
                        (9, 3)
                    ]

                    for (offset_x, offset_y), color in zip(
                        offsets,
                        colors
                    ):

                        painter.setBrush(
                            QColor(color)
                        )

                        painter.drawEllipse(
                            int(food["x"] + offset_x - 8),
                            int(food["y"] + offset_y - 8),
                            16,
                            16
                        )

                else:

                    painter.setBrush(
                        QColor("#8a7a5c")
                    )

                    painter.drawEllipse(
                        int(food["x"] - 14),
                        int(food["y"] - 14),
                        28,
                        28
                    )

                    painter.setBrush(
                        QColor("#5f5a3c")
                    )

                    painter.drawEllipse(
                        int(food["x"] - 9),
                        int(food["y"] - 9),
                        7,
                        7
                    )

                    painter.drawEllipse(
                        int(food["x"] + 3),
                        int(food["y"] + 3),
                        6,
                        6
                    )

                painter.setPen(
                    QColor("#c9b78a")
                )

                painter.setFont(
                    QFont(
                        "Segoe UI",
                        8,
                        QFont.Bold
                    )
                )

                painter.drawText(
                    int(food["x"] - 26),
                    int(food["y"] + 24),
                    "ROTTEN "
                    +
                    food["type"].upper()
                )

                painter.setFont(
                    QFont(
                        "Segoe UI",
                        8
                    )
                )

                painter.setPen(
                    QColor("#d47a5a")
                )

                painter.drawText(
                    int(food["x"] - 26),
                    int(food["y"] + 38),
                    "reward "
                    +
                    str(food["reward"])
                    +
                    " · "
                    +
                    food["taste"]
                )

                continue

            food_type = food["type"]

            if food_type == "Banana":

                painter.setPen(
                    Qt.NoPen
                )

                painter.setBrush(
                    QColor("#e7d34f")
                )

                painter.drawChord(
                    int(food["x"] - 18),
                    int(food["y"] - 10),
                    36,
                    24,
                    0,
                    180 * 16
                )

                painter.setPen(
                    QPen(
                        QColor("#8a7a1e"),
                        2
                    )
                )

                painter.drawLine(
                    int(food["x"] - 18),
                    int(food["y"]),
                    int(food["x"] - 25),
                    int(food["y"] - 6)
                )

            elif food_type == "Orange":

                painter.setPen(
                    Qt.NoPen
                )

                painter.setBrush(
                    QColor("#ff9a3d")
                )

                painter.drawEllipse(
                    int(food["x"] - 15),
                    int(food["y"] - 15),
                    30,
                    30
                )

                painter.setBrush(
                    QColor("#6fae3f")
                )

                painter.drawEllipse(
                    int(food["x"] - 4),
                    int(food["y"] - 25),
                    8,
                    12
                )

            elif food_type == "Strawberry":

                painter.setPen(
                    Qt.NoPen
                )

                painter.setBrush(
                    QColor("#ff5a5f")
                )

                painter.drawEllipse(
                    int(food["x"] - 12),
                    int(food["y"] - 8),
                    24,
                    27
                )

                painter.setBrush(
                    QColor("#55b86a")
                )

                painter.drawEllipse(
                    int(food["x"] - 6),
                    int(food["y"] - 15),
                    12,
                    8
                )

                painter.setPen(
                    QPen(
                        QColor("#b01116"),
                        2
                    )
                )

                painter.drawPoint(
                    int(food["x"] - 4),
                    int(food["y"])
                )

                painter.drawPoint(
                    int(food["x"] + 4),
                    int(food["y"] - 2)
                )

                painter.drawPoint(
                    int(food["x"]),
                    int(food["y"] + 4)
                )

            elif food_type == "Grape":

                colors = [
                    "#9b59b6",
                    "#8e44ad",
                    "#7d3c98",
                    "#a569bd"
                ]

                offsets = [
                    (-9, -6),
                    (3, -6),
                    (-3, 3),
                    (9, 3)
                ]

                painter.setPen(
                    Qt.NoPen
                )

                for (offset_x, offset_y), color in zip(
                    offsets,
                    colors
                ):

                    painter.setBrush(
                        QColor(color)
                    )

                    painter.drawEllipse(
                        int(food["x"] + offset_x - 8),
                        int(food["y"] + offset_y - 8),
                        16,
                        16
                    )

                painter.setPen(
                    QPen(
                        QColor("#6d8d3f"),
                        2
                    )
                )

                painter.drawLine(
                    int(food["x"]),
                    int(food["y"] - 11),
                    int(food["x"]),
                    int(food["y"] - 20)
                )

            else:

                painter.setPen(
                    Qt.NoPen
                )

                painter.setBrush(
                    QColor("#e63d3d")
                )

                painter.drawEllipse(
                    int(food["x"] - 14),
                    int(food["y"] - 14),
                    28,
                    28
                )

                painter.setBrush(
                    QColor("#a51f28")
                )

                painter.drawEllipse(
                    int(food["x"] - 8),
                    int(food["y"] - 7),
                    6,
                    6
                )

                painter.setBrush(
                    QColor("#55b86a")
                )

                painter.drawEllipse(
                    int(food["x"] + 3),
                    int(food["y"] - 16),
                    10,
                    5
                )

            painter.setPen(
                QColor("#eeeeee")
            )

            painter.setFont(
                QFont(
                    "Segoe UI",
                    9,
                    QFont.Bold
                )
            )

            painter.drawText(
                int(food["x"] - 22),
                int(food["y"] + 30),
                food["type"].upper()
            )

        vision_length = 105

        left_angle = (
            self.fly_angle
            -
            self.vision_angle / 2
        )

        right_angle = (
            self.fly_angle
            +
            self.vision_angle / 2
        )

        painter.setPen(
            QPen(
                QColor(70, 150, 255, 150),
                2
            )
        )

        painter.drawLine(
            int(self.fly_x),
            int(self.fly_y),
            int(
                self.fly_x
                +
                math.cos(left_angle)
                *
                vision_length
            ),
            int(
                self.fly_y
                +
                math.sin(left_angle)
                *
                vision_length
            )
        )

        painter.drawLine(
            int(self.fly_x),
            int(self.fly_y),
            int(
                self.fly_x
                +
                math.cos(right_angle)
                *
                vision_length
            ),
            int(
                self.fly_y
                +
                math.sin(right_angle)
                *
                vision_length
            )
        )

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QColor("#222936")
        )

        painter.drawEllipse(
            int(self.fly_x - 14),
            int(self.fly_y - 9),
            28,
            18
        )

        painter.setBrush(
            QColor(170, 190, 210, 130)
        )

        painter.drawEllipse(
            int(self.fly_x - 12),
            int(self.fly_y - 17),
            14,
            9
        )

        painter.drawEllipse(
            int(self.fly_x + 1),
            int(self.fly_y - 17),
            14,
            9
        )

        painter.setBrush(
            QColor("#d8a33e")
        )

        painter.drawEllipse(
            int(self.fly_x - 7),
            int(self.fly_y - 8),
            17,
            16
        )

        painter.setBrush(
            QColor("#151821")
        )

        painter.drawEllipse(
            int(self.fly_x + 5),
            int(self.fly_y - 6),
            7,
            7
        )

        painter.setPen(
            QPen(
                QColor("#d8a33e"),
                2
            )
        )

        painter.drawLine(
            int(self.fly_x - 7),
            int(self.fly_y - 5),
            int(
                self.fly_x
                -
                17
                +
                math.cos(self.fly_angle + 0.5) * 10
            ),
            int(
                self.fly_y
                +
                math.sin(self.fly_angle + 0.5) * 10
            )
        )

        painter.drawLine(
            int(self.fly_x - 7),
            int(self.fly_y + 3),
            int(
                self.fly_x
                -
                17
                +
                math.cos(self.fly_angle - 0.5) * 10
            ),
            int(
                self.fly_y
                +
                math.sin(self.fly_angle - 0.5) * 10
            )
        )

        painter.setPen(
            QColor("#ffffff")
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                10,
                QFont.Bold
            )
        )

        painter.drawText(
            15,
            25,
            "2D FLY SANDBOX"
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                9
            )
        )

        painter.setPen(
            QColor("#9ba7b9")
        )

        painter.drawText(
            15,
            47,
            "Left-drag to move objects · Right-click for options · Keys: A fruit, O obstacle, R rotate, D duplicate, Del delete, M rotten, L/T/N resize, Space start/pause"
        )

        painter.drawText(
            15,
            height - 18,
            "Food collected: "
            + str(self.food_collected)
            +
            "    Total reward: "
            +
            str(self.total_reward)
        )


class FlySandbox(QWidget):

    def __init__(self):
        super().__init__()

        self.canvas = SandboxCanvas()

        layout = QVBoxLayout()
        layout.setSpacing(10)

        title_row = QHBoxLayout()

        title = QLabel(
            "🪰 Fruit Fly Sandbox"
        )

        title.setObjectName(
            "sectionTitle"
        )

        title_row.addWidget(title)
        title_row.addStretch()

        self.status_label = QLabel(
            "Paused"
        )

        self.status_label.setObjectName(
            "sandboxStatus"
        )

        title_row.addWidget(
            self.status_label
        )

        layout.addLayout(
            title_row
        )

        description = QLabel(
            "A 2D sensory sandbox. The fly detects, approaches and tastes different fruits, then builds a basic memory. Drag the fly, fruit and obstacles with your mouse. Right-click an object for edit options, or use the shortcut keys."
        )

        description.setObjectName(
            "smallText"
        )

        description.setWordWrap(True)

        layout.addWidget(
            description
        )

        layout.addWidget(
            self.canvas,
            1
        )

        controls = QHBoxLayout()

        self.start_button = QPushButton(
            "▶ Start"
        )

        self.start_button.setObjectName(
            "primaryButton"
        )

        self.start_button.clicked.connect(
            self.start
        )

        pause_button = QPushButton(
            "⏸ Pause"
        )

        pause_button.clicked.connect(
            self.pause
        )

        reset_button = QPushButton(
            "↻ Reset"
        )

        reset_button.clicked.connect(
            self.reset
        )

        fruit_label = QLabel(
            "Fruit"
        )

        self.fruit_box = QComboBox()

        self.fruit_box.addItems(
            list(FRUIT_TYPES.keys())
        )

        self.fruit_box.setCurrentText(
            "Apple"
        )

        self.fruit_box.currentTextChanged.connect(
            self.set_selected_fruit_type
        )

        fruit_button = QPushButton(
            "🍎 Add Fruit"
        )

        fruit_button.clicked.connect(
            self.add_fruit
        )

        obstacle_button = QPushButton(
            "🧱 Add Obstacle"
        )

        obstacle_button.clicked.connect(
            self.add_obstacle
        )

        controls.addWidget(
            self.start_button
        )

        controls.addWidget(
            pause_button
        )

        controls.addWidget(
            reset_button
        )

        controls.addWidget(
            fruit_label
        )

        controls.addWidget(
            self.fruit_box
        )

        controls.addWidget(
            fruit_button
        )

        controls.addWidget(
            obstacle_button
        )

        controls.addStretch()

        speed_label = QLabel(
            "Speed"
        )

        self.speed_box = QComboBox()

        self.speed_box.addItems([
            "0.5x",
            "1x",
            "2x",
            "4x"
        ])

        self.speed_box.setCurrentText(
            "1x"
        )

        self.speed_box.currentTextChanged.connect(
            self.speed_changed
        )

        controls.addWidget(
            speed_label
        )

        controls.addWidget(
            self.speed_box
        )

        layout.addLayout(
            controls
        )

        information_row = QHBoxLayout()

        senses_frame = self.create_senses_panel()
        brain_frame = self.create_brain_panel()
        memory_frame = self.create_memory_panel()

        information_row.addWidget(
            senses_frame,
            1
        )

        information_row.addWidget(
            brain_frame,
            1
        )

        information_row.addWidget(
            memory_frame,
            1
        )

        layout.addLayout(
            information_row
        )

        self.setLayout(
            layout
        )

        self.canvas.state_changed.connect(
            self.update_panels
        )

        self.update_panels()

    def create_panel_frame(self):

        frame = QFrame()

        frame.setObjectName(
            "sandboxPanel"
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            15,
            12,
            15,
            12
        )

        frame.setLayout(
            layout
        )

        return frame, layout

    def create_senses_panel(self):

        frame, layout = self.create_panel_frame()

        title = QLabel(
            "👁 Sensory Activity"
        )

        title.setObjectName(
            "subTitle"
        )

        layout.addWidget(
            title
        )

        self.vision_bar = self.create_activity_bar()
        self.smell_bar = self.create_activity_bar()
        self.taste_bar = self.create_activity_bar()

        self.vision_value = QLabel("0%")
        self.smell_value = QLabel("0%")
        self.taste_value = QLabel("0%")

        self.add_bar_row(
            layout,
            "Vision",
            self.vision_bar,
            self.vision_value
        )

        self.add_bar_row(
            layout,
            "Smell",
            self.smell_bar,
            self.smell_value
        )

        self.add_bar_row(
            layout,
            "Taste",
            self.taste_bar,
            self.taste_value
        )

        return frame

    def create_brain_panel(self):

        frame, layout = self.create_panel_frame()

        title = QLabel(
            "🧠 Brain Activity"
        )

        title.setObjectName(
            "subTitle"
        )

        layout.addWidget(
            title
        )

        self.brain_bars = {}
        self.brain_values = {}

        for name in [
            "Antennal Lobe",
            "Visual Neurons",
            "Kenyon Cells",
            "Mushroom Body",
            "Central Complex",
            "Descending Neurons"
        ]:

            bar = self.create_activity_bar()

            value = QLabel(
                "0%"
            )

            self.brain_bars[name] = bar
            self.brain_values[name] = value

            self.add_bar_row(
                layout,
                name,
                bar,
                value
            )

        return frame

    def create_memory_panel(self):

        frame, layout = self.create_panel_frame()

        title = QLabel(
            "🧠 Memories"
        )

        title.setObjectName(
            "subTitle"
        )

        layout.addWidget(
            title
        )

        self.memory_text = QTextEdit()

        self.memory_text.setReadOnly(
            True
        )

        self.memory_text.setMinimumHeight(
            150
        )

        self.memory_text.setPlaceholderText(
            "The fly has not learned anything yet."
        )

        layout.addWidget(
            self.memory_text
        )

        self.food_label = QLabel(
            "Food collected: 0"
        )

        layout.addWidget(
            self.food_label
        )

        return frame

    def create_activity_bar(self):

        bar = QProgressBar()

        bar.setRange(
            0,
            100
        )

        bar.setValue(
            0
        )

        bar.setTextVisible(
            False
        )

        bar.setFixedHeight(
            10
        )

        return bar

    def add_bar_row(
        self,
        layout,
        name,
        bar,
        value
    ):

        row = QHBoxLayout()

        label = QLabel(
            name
        )

        label.setMinimumWidth(
            125
        )

        row.addWidget(
            label
        )

        row.addWidget(
            bar,
            1
        )

        value.setMinimumWidth(
            40
        )

        value.setAlignment(
            Qt.AlignRight
        )

        row.addWidget(
            value
        )

        layout.addLayout(
            row
        )

    def start(self):

        self.canvas.start()
        self.status_label.setText(
            "● Running"
        )

    def pause(self):

        self.canvas.pause()
        self.status_label.setText(
            "Ⅱ Paused"
        )

    def reset(self):

        self.canvas.reset()
        self.status_label.setText(
            "Reset"
        )

    def set_selected_fruit_type(self, fruit_type):

        self.canvas.selected_fruit_type = fruit_type

    def add_fruit(self):

        fruit_type = self.fruit_box.currentText()

        self.canvas.add_fruit(
            fruit_type
        )

    def add_obstacle(self):

        self.canvas.add_obstacle()

    def speed_changed(self, value):

        multiplier = float(
            value.replace(
                "x",
                ""
            )
        )

        self.canvas.set_speed(
            multiplier
        )

    def update_panels(self):

        if self.canvas.running:

            self.status_label.setText(
                "● Running"
            )

        else:

            self.status_label.setText(
                "Ⅱ Paused"
            )

        vision = int(
            self.canvas.vision_activity * 100
        )

        smell = int(
            self.canvas.smell_activity * 100
        )

        taste = int(
            self.canvas.taste_activity * 100
        )

        self.vision_bar.setValue(
            vision
        )

        self.smell_bar.setValue(
            smell
        )

        self.taste_bar.setValue(
            taste
        )

        self.vision_value.setText(
            str(vision) + "%"
        )

        self.smell_value.setText(
            str(smell) + "%"
        )

        self.taste_value.setText(
            str(taste) + "%"
        )

        for name, value in self.canvas.brain_activity.items():

            percentage = int(
                max(
                    0,
                    min(
                        1,
                        value
                    )
                )
                * 100
            )

            self.brain_bars[name].setValue(
                percentage
            )

            self.brain_values[name].setText(
                str(percentage) + "%"
            )

        if not self.canvas.memories:

            self.memory_text.setText(
                "No memories yet.\n\n"
                "The fly needs to reach a fruit and taste it."
            )

        else:

            lines = []

            for name, memory in self.canvas.memories.items():

                emoji = SAND_FRUIT_EMOJI.get(
                    memory.get(
                        "type",
                        name
                    ),
                    "🍎"
                )

                display_name = memory.get(
                    "type",
                    name
                )

                strength = min(
                    1,
                    0.30 + memory["seen"] * 0.20
                )

                strength_percent = int(
                    strength * 100
                )

                sign = "+"

                if memory["reward"] < 0:

                    sign = ""

                state_tag = memory.get(
                    "state",
                    "FRESH"
                )

                lines.append(
                    emoji
                    + " "
                    + display_name
                    + " ("
                    + state_tag
                    + ") — "
                    + memory["taste"]
                    + " — Reward "
                    + sign
                    + str(memory["reward"])
                    + " — Seen "
                    + str(memory["seen"])
                    + " time(s) — Memory "
                    + str(strength_percent)
                    + "%"
                )

            self.memory_text.setText(
                "\n".join(lines)
            )

        self.food_label.setText(
            "Food collected: "
            +
            str(self.canvas.food_collected)
            +
            "    Total reward: "
            +
            str(self.canvas.total_reward)
        )


class LoginWindow(QDialog):

    def __init__(self):
        super().__init__()

        self.client = None

        self.setWindowTitle(
            "Sign in to neuPrint"
        )

        self.setFixedSize(
            580,
            500
        )

        layout = QVBoxLayout()

        layout.setSpacing(
            12
        )

        layout.setContentsMargins(
            35,
            30,
            35,
            30
        )

        title = QLabel(
            "Fruit Fly Brain Explorer"
        )

        title.setObjectName(
            "loginTitle"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        subtitle = QLabel(
            "Connect to the neuPrint fruit fly connectome"
        )

        subtitle.setObjectName(
            "loginSubtitle"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        server_label = QLabel(
            "neuPrint Server"
        )

        server_label.setObjectName(
            "fieldLabel"
        )

        self.server_box = QLineEdit(
            SERVER
        )

        self.server_box.setReadOnly(
            True
        )

        layout.addWidget(
            server_label
        )

        layout.addWidget(
            self.server_box
        )

        dataset_label = QLabel(
            "Dataset"
        )

        dataset_label.setObjectName(
            "fieldLabel"
        )

        self.dataset_box = QLineEdit(
            DATASET
        )

        self.dataset_box.setReadOnly(
            True
        )

        layout.addWidget(
            dataset_label
        )

        layout.addWidget(
            self.dataset_box
        )

        token_label = QLabel(
            "neuPrint API Token"
        )

        token_label.setObjectName(
            "fieldLabel"
        )

        self.token_box = QLineEdit()

        self.token_box.setEchoMode(
            QLineEdit.Password
        )

        self.token_box.setPlaceholderText(
            "Paste your neuPrint API token here"
        )

        layout.addWidget(
            token_label
        )

        layout.addWidget(
            self.token_box
        )

        self.remember_checkbox = QCheckBox(
            "Remember my API token"
        )

        layout.addWidget(
            self.remember_checkbox
        )

        saved_token = self.load_saved_token()

        if saved_token:

            self.token_box.setText(
                saved_token
            )

            self.remember_checkbox.setChecked(
                True
            )

        token_info = QLabel(
            "If enabled, the token is stored using your computer's "
            "credential storage instead of being written into the app."
        )

        token_info.setObjectName(
            "smallText"
        )

        token_info.setWordWrap(
            True
        )

        layout.addWidget(
            token_info
        )

        browser_button = QPushButton(
            "Open neuPrint in Browser"
        )

        browser_button.clicked.connect(
            self.open_neuprint
        )

        layout.addWidget(
            browser_button
        )

        login_button = QPushButton(
            "Sign In and Connect"
        )

        login_button.setObjectName(
            "primaryButton"
        )

        login_button.clicked.connect(
            self.login
        )

        layout.addWidget(
            login_button
        )

        clear_button = QPushButton(
            "Forget Saved Token"
        )

        clear_button.clicked.connect(
            self.clear_saved_token
        )

        layout.addWidget(
            clear_button
        )

        self.setLayout(
            layout
        )

    def load_saved_token(self):

        try:

            return keyring.get_password(
                KEYRING_SERVICE,
                KEYRING_USERNAME
            )

        except Exception:

            return None

    def save_token(self, token):

        try:

            keyring.set_password(
                KEYRING_SERVICE,
                KEYRING_USERNAME,
                token
            )

            return True

        except Exception:

            return False

    def clear_saved_token(self):

        try:

            keyring.delete_password(
                KEYRING_SERVICE,
                KEYRING_USERNAME
            )

        except Exception:

            pass

        self.token_box.clear()

        self.remember_checkbox.setChecked(
            False
        )

        QMessageBox.information(
            self,
            "Saved Token Removed",
            "The saved neuPrint token has been removed."
        )

    def open_neuprint(self):

        QDesktopServices.openUrl(
            QUrl(
                "https://neuprint.janelia.org/"
            )
        )

    def login(self):

        token = self.token_box.text().strip()

        if not token:

            QMessageBox.warning(
                self,
                "Token Required",
                "Please enter your neuPrint API token."
            )

            return

        try:

            client = Client(
                SERVER,
                dataset=DATASET,
                token=token,
                progress=False
            )

            client.fetch_profile()

            if self.remember_checkbox.isChecked():

                self.save_token(
                    token
                )

            else:

                try:

                    keyring.delete_password(
                        KEYRING_SERVICE,
                        KEYRING_USERNAME
                    )

                except Exception:

                    pass

            self.client = client

            QMessageBox.information(
                self,
                "Connected",
                "Successfully connected to neuPrint."
            )

            self.accept()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Connection Failed",
                "Could not connect to neuPrint.\n\n"
                +
                str(error)
            )


class MainWindow(QMainWindow):

    def __init__(self, client):

        super().__init__()

        self.client = client

        self.history = []
        self.favorites = []
        self.current_neuron = None
        self.current_dataframe = None

        self.setWindowTitle(
            "Fruit Fly Brain Explorer - neuPrint"
        )

        self.resize(
            1450,
            900
        )

        self.build_ui()

    def build_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QHBoxLayout()

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        main_layout.setSpacing(
            0
        )

        sidebar = self.create_sidebar()

        main_layout.addWidget(
            sidebar
        )

        content = QWidget()

        content_layout = QVBoxLayout()

        content_layout.setContentsMargins(
            20,
            20,
            20,
            20
        )

        header = QHBoxLayout()

        title = QLabel(
            "Fruit Fly Brain Explorer"
        )

        title.setObjectName(
            "mainTitle"
        )

        connection_label = QLabel(
            "● Connected to neuPrint"
        )

        connection_label.setObjectName(
            "connected"
        )

        header.addWidget(
            title
        )

        header.addStretch()

        header.addWidget(
            connection_label
        )

        content_layout.addLayout(
            header
        )

        self.tabs = QTabWidget()

        self.search_tab = self.create_search_tab()
        self.data_tab = self.create_data_tab()
        self.analytics_tab = self.create_analytics_tab()
        self.sandbox_tab = FlySandbox()
        self.inspector_tab = self.create_inspector_tab()
        self.connections_tab = self.create_connections_tab()
        self.history_tab = self.create_history_tab()
        self.favorites_tab = self.create_favorites_tab()
        self.tools_tab = self.create_tools_tab()

        self.tabs.addTab(
            self.search_tab,
            "Search"
        )

        self.tabs.addTab(
            self.data_tab,
            "Data Explorer"
        )

        self.tabs.addTab(
            self.analytics_tab,
            "Analytics"
        )

        self.tabs.addTab(
            self.sandbox_tab,
            "🪰 Sandbox"
        )

        self.tabs.addTab(
            self.inspector_tab,
            "Neuron Inspector"
        )

        self.tabs.addTab(
            self.connections_tab,
            "Connections"
        )

        self.tabs.addTab(
            self.history_tab,
            "History"
        )

        self.tabs.addTab(
            self.favorites_tab,
            "Favorites"
        )

        self.tabs.addTab(
            self.tools_tab,
            "Tools"
        )

        content_layout.addWidget(
            self.tabs
        )

        content.setLayout(
            content_layout
        )

        main_layout.addWidget(
            content,
            1
        )

        central.setLayout(
            main_layout
        )

    def create_sidebar(self):

        frame = QFrame()

        frame.setObjectName(
            "sidebar"
        )

        frame.setFixedWidth(
            315
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            18,
            20,
            18,
            20
        )

        layout.setSpacing(
            8
        )

        logo = QLabel(
            "🧠"
        )

        logo.setAlignment(
            Qt.AlignCenter
        )

        logo.setObjectName(
            "logo"
        )

        layout.addWidget(
            logo
        )

        sandbox_button = QPushButton(
            "🪰 Open Fly Sandbox"
        )

        sandbox_button.setObjectName(
            "primaryButton"
        )

        sandbox_button.clicked.connect(
            lambda:
            self.tabs.setCurrentWidget(
                self.sandbox_tab
            )
        )

        layout.addWidget(
            sandbox_button
        )

        sidebar_title = QLabel(
            "Brain Structures"
        )

        sidebar_title.setObjectName(
            "sidebarTitle"
        )

        layout.addWidget(
            sidebar_title
        )

        for name in BRAIN_PARTS:

            row = QHBoxLayout()

            button = QPushButton(
                name
            )

            button.setObjectName(
                "brainButton"
            )

            button.clicked.connect(
                lambda checked=False, n=name:
                self.search_brain_part(n)
            )

            info_button = QPushButton(
                "ⓘ"
            )

            info_button.setObjectName(
                "infoButton"
            )

            info_button.setFixedSize(
                34,
                34
            )

            info_button.setToolTip(
                "Show information"
            )

            info_button.clicked.connect(
                lambda checked=False, n=name:
                self.show_brain_info(n)
            )

            row.addWidget(
                button
            )

            row.addWidget(
                info_button
            )

            layout.addLayout(
                row
            )

        layout.addStretch()

        website_button = QPushButton(
            "Open neuPrint Website"
        )

        website_button.clicked.connect(
            self.open_neuprint
        )

        layout.addWidget(
            website_button
        )

        signout_button = QPushButton(
            "Sign Out"
        )

        signout_button.clicked.connect(
            self.sign_out
        )

        layout.addWidget(
            signout_button
        )

        frame.setLayout(
            layout
        )

        return frame

    def show_brain_info(self, name):

        data = BRAIN_PARTS[name]

        QMessageBox.information(
            self,
            "About " + name,
            name
            +
            "\n\n"
            +
            data["description"]
            +
            "\n\n"
            +
            "neuPrint search code: "
            +
            data["search"]
        )

    def open_neuprint(self):

        QDesktopServices.openUrl(
            QUrl(
                "https://neuprint.janelia.org/"
            )
        )

    def create_search_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        layout.setSpacing(
            15
        )

        heading = QLabel(
            "Search Neurons"
        )

        heading.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            heading
        )

        search_row = QHBoxLayout()

        self.search_type = QComboBox()

        self.search_type.addItems([
            "Neuron Type",
            "Neuron Instance",
            "Body ID"
        ])

        self.search_box = QLineEdit()

        self.search_box.setPlaceholderText(
            "Enter neuron type, instance or body ID"
        )

        self.search_box.returnPressed.connect(
            self.search_neurons
        )

        self.exact_checkbox = QCheckBox(
            "Exact match"
        )

        search_button = QPushButton(
            "Search"
        )

        search_button.setObjectName(
            "primaryButton"
        )

        search_button.clicked.connect(
            self.search_neurons
        )

        search_row.addWidget(
            self.search_type
        )

        search_row.addWidget(
            self.search_box,
            1
        )

        search_row.addWidget(
            self.exact_checkbox
        )

        search_row.addWidget(
            search_button
        )

        layout.addLayout(
            search_row
        )

        self.search_status = QLabel(
            "Ready to search neuPrint."
        )

        self.search_status.setObjectName(
            "status"
        )

        layout.addWidget(
            self.search_status
        )

        info = QLabel(
            "Examples: MBON, KC, DNge, LC, AL, LH, FB, EB"
        )

        info.setObjectName(
            "smallText"
        )

        layout.addWidget(
            info
        )

        quick_title = QLabel(
            "Quick Search"
        )

        quick_title.setObjectName(
            "subTitle"
        )

        layout.addWidget(
            quick_title
        )

        quick_row = QHBoxLayout()

        for index, (name, data) in enumerate(
            BRAIN_PARTS.items()
        ):

            if index >= 5:
                break

            button = QPushButton(
                data["search"]
            )

            button.setToolTip(
                name
            )

            button.clicked.connect(
                lambda checked=False, value=data["search"]:
                self.quick_search(value)
            )

            quick_row.addWidget(
                button
            )

        layout.addLayout(
            quick_row
        )

        layout.addStretch()

        widget.setLayout(
            layout
        )

        return widget

    def quick_search(self, value):

        self.search_type.setCurrentText(
            "Neuron Type"
        )

        self.search_box.setText(
            value
        )

        self.exact_checkbox.setChecked(
            False
        )

        self.search_neurons()

    def create_data_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        title = QLabel(
            "Data Explorer"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            title
        )

        button_row = QHBoxLayout()

        csv_button = QPushButton(
            "Export CSV"
        )

        csv_button.clicked.connect(
            self.export_csv
        )

        json_button = QPushButton(
            "Export JSON"
        )

        json_button.clicked.connect(
            self.export_json
        )

        button_row.addWidget(
            csv_button
        )

        button_row.addWidget(
            json_button
        )

        button_row.addStretch()

        layout.addLayout(
            button_row
        )

        self.table = QTableWidget()

        self.table.setColumnCount(
            3
        )

        self.table.setHorizontalHeaderLabels([
            "Body ID",
            "Type",
            "Instance"
        ])

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.itemSelectionChanged.connect(
            self.table_selection_changed
        )

        layout.addWidget(
            self.table
        )

        widget.setLayout(
            layout
        )

        return widget

    def create_analytics_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        title = QLabel(
            "Analytics"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            title
        )

        self.analytics_text = QTextEdit()

        self.analytics_text.setReadOnly(
            True
        )

        self.analytics_text.setText(
            "Search for neurons to see analytics."
        )

        layout.addWidget(
            self.analytics_text
        )

        widget.setLayout(
            layout
        )

        return widget

    def create_inspector_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        title = QLabel(
            "Neuron Inspector"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            title
        )

        self.inspector_text = QTextEdit()

        self.inspector_text.setReadOnly(
            True
        )

        self.inspector_text.setText(
            "Select a neuron from the Data Explorer."
        )

        layout.addWidget(
            self.inspector_text
        )

        button_row = QHBoxLayout()

        favorite_button = QPushButton(
            "⭐ Add to Favorites"
        )

        favorite_button.clicked.connect(
            self.add_favorite
        )

        neuprint_button = QPushButton(
            "Open Neuron in neuPrint"
        )

        neuprint_button.clicked.connect(
            self.open_current_neuron
        )

        button_row.addWidget(
            favorite_button
        )

        button_row.addWidget(
            neuprint_button
        )

        layout.addLayout(
            button_row
        )

        widget.setLayout(
            layout
        )

        return widget

    def create_connections_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        title = QLabel(
            "Neuron Connections"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            title
        )

        controls = QHBoxLayout()

        min_weight_label = QLabel(
            "Minimum synapses:"
        )

        self.min_weight = QSpinBox()

        self.min_weight.setMinimum(
            1
        )

        self.min_weight.setMaximum(
            10000
        )

        self.min_weight.setValue(
            1
        )

        upstream_button = QPushButton(
            "Load Upstream"
        )

        upstream_button.clicked.connect(
            lambda:
            self.load_connections(
                "upstream"
            )
        )

        downstream_button = QPushButton(
            "Load Downstream"
        )

        downstream_button.clicked.connect(
            lambda:
            self.load_connections(
                "downstream"
            )
        )

        controls.addWidget(
            min_weight_label
        )

        controls.addWidget(
            self.min_weight
        )

        controls.addWidget(
            upstream_button
        )

        controls.addWidget(
            downstream_button
        )

        controls.addStretch()

        layout.addLayout(
            controls
        )

        self.connections_table = QTableWidget()

        self.connections_table.setColumnCount(
            4
        )

        self.connections_table.setHorizontalHeaderLabels([
            "Body ID",
            "Type",
            "Instance",
            "Synapses"
        ])

        self.connections_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.connections_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.connections_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        layout.addWidget(
            self.connections_table
        )

        widget.setLayout(
            layout
        )

        return widget

    def create_history_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        title = QLabel(
            "Search History"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            title
        )

        clear_button = QPushButton(
            "Clear History"
        )

        clear_button.clicked.connect(
            self.clear_history
        )

        layout.addWidget(
            clear_button
        )

        self.history_list = QTextEdit()

        self.history_list.setReadOnly(
            True
        )

        self.history_list.setText(
            "No searches yet."
        )

        layout.addWidget(
            self.history_list
        )

        widget.setLayout(
            layout
        )

        return widget

    def create_favorites_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        title = QLabel(
            "Favorites"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            title
        )

        remove_button = QPushButton(
            "Remove Selected Favorite"
        )

        remove_button.clicked.connect(
            self.remove_favorite
        )

        layout.addWidget(
            remove_button
        )

        self.favorites_table = QTableWidget()

        self.favorites_table.setColumnCount(
            3
        )

        self.favorites_table.setHorizontalHeaderLabels([
            "Body ID",
            "Type",
            "Instance"
        ])

        self.favorites_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.favorites_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.favorites_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        layout.addWidget(
            self.favorites_table
        )

        widget.setLayout(
            layout
        )

        return widget

    def create_tools_tab(self):

        widget = QWidget()

        layout = QVBoxLayout()

        title = QLabel(
            "Tools & Settings"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            title
        )

        dataset_label = QLabel(
            "Dataset: "
            +
            DATASET
        )

        server_label = QLabel(
            "Server: "
            +
            SERVER
        )

        layout.addWidget(
            dataset_label
        )

        layout.addWidget(
            server_label
        )

        layout.addSpacing(
            15
        )

        website_button = QPushButton(
            "Open neuPrint Website"
        )

        website_button.clicked.connect(
            self.open_neuprint
        )

        layout.addWidget(
            website_button
        )

        export_csv_button = QPushButton(
            "Export Current Search as CSV"
        )

        export_csv_button.clicked.connect(
            self.export_csv
        )

        layout.addWidget(
            export_csv_button
        )

        export_json_button = QPushButton(
            "Export Current Search as JSON"
        )

        export_json_button.clicked.connect(
            self.export_json
        )

        layout.addWidget(
            export_json_button
        )

        layout.addStretch()

        widget.setLayout(
            layout
        )

        return widget

    def search_brain_part(self, name):

        code = BRAIN_PARTS[name]["search"]

        self.search_type.setCurrentText(
            "Neuron Type"
        )

        self.search_box.setText(
            code
        )

        self.exact_checkbox.setChecked(
            False
        )

        self.tabs.setCurrentWidget(
            self.search_tab
        )

        self.search_neurons()

    def search_neurons(self):

        value = self.search_box.text().strip()

        if not value:

            QMessageBox.warning(
                self,
                "Search",
                "Please enter a search value."
            )

            return

        mode = self.search_type.currentText()
        exact = self.exact_checkbox.isChecked()

        try:

            self.search_status.setText(
                "Searching neuPrint..."
            )

            QApplication.processEvents()

            if mode == "Body ID":

                try:

                    body_id = int(value)

                except ValueError:

                    QMessageBox.warning(
                        self,
                        "Invalid Body ID",
                        "Body ID must be a number."
                    )

                    return

                criteria = NC(
                    bodyId=body_id
                )

            elif mode == "Neuron Instance":

                if exact:

                    criteria = NC(
                        instance=value
                    )

                else:

                    criteria = NC(
                        instance=".*"
                        +
                        value
                        +
                        ".*"
                    )

            else:

                if exact:

                    criteria = NC(
                        type=value
                    )

                else:

                    criteria = NC(
                        type=".*"
                        +
                        value
                        +
                        ".*"
                    )

            neurons, roi_counts = fetch_neurons(
                criteria,
                client=self.client
            )

            self.current_dataframe = neurons.copy()

            self.populate_neuron_table(
                neurons
            )

            result_count = len(
                neurons
            )

            self.search_status.setText(
                str(result_count)
                +
                " neuron(s) found."
            )

            self.history.insert(
                0,
                mode
                +
                ": "
                +
                value
            )

            self.history = self.history[:100]

            self.update_history()

            self.update_analytics(
                neurons,
                value,
                mode
            )

            self.tabs.setCurrentWidget(
                self.data_tab
            )

        except Exception as error:

            self.search_status.setText(
                "Search failed."
            )

            QMessageBox.critical(
                self,
                "neuPrint Search Error",
                str(error)
            )

    def populate_neuron_table(self, neurons):

        self.table.setRowCount(
            0
        )

        if neurons is None:
            return

        for _, neuron in neurons.iterrows():

            row = self.table.rowCount()

            self.table.insertRow(
                row
            )

            body_id = neuron.get(
                "bodyId",
                ""
            )

            neuron_type = neuron.get(
                "type",
                ""
            )

            instance = neuron.get(
                "instance",
                ""
            )

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(
                    str(body_id)
                )
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(
                    str(neuron_type)
                )
            )

            self.table.setItem(
                row,
                2,
                QTableWidgetItem(
                    str(instance)
                )
            )

    def update_analytics(
        self,
        neurons,
        query,
        mode
    ):

        if neurons is None or len(neurons) == 0:

            self.analytics_text.setText(
                "No results."
            )

            return

        text = ""

        text += "SEARCH ANALYTICS\n"
        text += "=================\n\n"

        text += "Query: "
        text += query
        text += "\n"

        text += "Search mode: "
        text += mode
        text += "\n"

        text += "Total neurons: "
        text += str(len(neurons))
        text += "\n\n"

        if "type" in neurons.columns:

            type_counts = (
                neurons["type"]
                .fillna("Unknown")
                .value_counts()
                .head(15)
            )

            text += "Most common neuron types:\n\n"

            for neuron_type, count in type_counts.items():

                text += (
                    str(neuron_type)
                    +
                    "  —  "
                    +
                    str(count)
                    +
                    "\n"
                )

        if "instance" in neurons.columns:

            instance_count = (
                neurons["instance"]
                .notna()
                .sum()
            )

            text += (
                "\nNeurons with instance names: "
                +
                str(instance_count)
            )

        self.analytics_text.setText(
            text
        )

    def table_selection_changed(self):

        selected = self.table.selectedItems()

        if not selected:
            return

        row = selected[0].row()

        body_id = self.table.item(
            row,
            0
        ).text()

        neuron_type = self.table.item(
            row,
            1
        ).text()

        instance = self.table.item(
            row,
            2
        ).text()

        self.current_neuron = {
            "bodyId": body_id,
            "type": neuron_type,
            "instance": instance
        }

        self.inspector_text.setText(
            "NEURON INFORMATION\n"
            "===================\n\n"
            "Body ID: "
            +
            body_id
            +
            "\n\n"
            "Type: "
            +
            neuron_type
            +
            "\n\n"
            "Instance: "
            +
            instance
            +
            "\n\n"
            "Dataset: "
            +
            DATASET
            +
            "\n\n"
            "Server: "
            +
            SERVER
        )

        self.tabs.setCurrentWidget(
            self.inspector_tab
        )

    def open_current_neuron(self):

        if not self.current_neuron:

            QMessageBox.information(
                self,
                "Neuron",
                "Select a neuron first."
            )

            return

        body_id = self.current_neuron[
            "bodyId"
        ]

        url = (
            "https://neuprint.janelia.org/"
            "?bodyId="
            +
            str(body_id)
        )

        QDesktopServices.openUrl(
            QUrl(url)
        )

    def add_favorite(self):

        if not self.current_neuron:

            QMessageBox.information(
                self,
                "Favorites",
                "Select a neuron first."
            )

            return

        body_id = self.current_neuron[
            "bodyId"
        ]

        for neuron in self.favorites:

            if neuron["bodyId"] == body_id:

                QMessageBox.information(
                    self,
                    "Favorites",
                    "This neuron is already a favorite."
                )

                return

        self.favorites.append(
            self.current_neuron.copy()
        )

        self.update_favorites()

        QMessageBox.information(
            self,
            "Favorites",
            "Neuron added to favorites."
        )

    def update_favorites(self):

        self.favorites_table.setRowCount(
            0
        )

        for neuron in self.favorites:

            row = self.favorites_table.rowCount()

            self.favorites_table.insertRow(
                row
            )

            self.favorites_table.setItem(
                row,
                0,
                QTableWidgetItem(
                    str(neuron["bodyId"])
                )
            )

            self.favorites_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    str(neuron["type"])
                )
            )

            self.favorites_table.setItem(
                row,
                2,
                QTableWidgetItem(
                    str(neuron["instance"])
                )
            )

    def remove_favorite(self):

        selected = (
            self.favorites_table.selectedItems()
        )

        if not selected:

            QMessageBox.information(
                self,
                "Favorites",
                "Select a favorite first."
            )

            return

        row = selected[0].row()

        if 0 <= row < len(
            self.favorites
        ):

            self.favorites.pop(
                row
            )

            self.update_favorites()

    def update_history(self):

        if not self.history:

            self.history_list.setText(
                "No searches yet."
            )

            return

        self.history_list.setText(
            "\n".join(
                self.history
            )
        )

    def clear_history(self):

        self.history.clear()

        self.update_history()

    def load_connections(
        self,
        direction
    ):

        if not self.current_neuron:

            QMessageBox.information(
                self,
                "Connections",
                "Select a neuron first."
            )

            return

        try:

            body_id = int(
                self.current_neuron[
                    "bodyId"
                ]
            )

            minimum = self.min_weight.value()

            neuron_criteria = NC(
                bodyId=body_id
            )

            if direction == "upstream":

                sources, targets, connections = (
                    fetch_adjacencies(
                        sources=None,
                        targets=neuron_criteria,
                        min_total_weight=minimum,
                        client=self.client
                    )
                )

                self.populate_connections(
                    sources,
                    connections,
                    direction
                )

            else:

                sources, targets, connections = (
                    fetch_adjacencies(
                        sources=neuron_criteria,
                        targets=None,
                        min_total_weight=minimum,
                        client=self.client
                    )
                )

                self.populate_connections(
                    targets,
                    connections,
                    direction
                )

            self.tabs.setCurrentWidget(
                self.connections_tab
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Connection Error",
                str(error)
            )

    def populate_connections(
        self,
        neurons,
        connections,
        direction
    ):

        self.connections_table.setRowCount(
            0
        )

        if neurons is None:
            return

        if connections is None:
            return

        if len(neurons) == 0:
            return

        weight_column = None

        for possible in [
            "weight",
            "synWeight",
            "totalWeight"
        ]:

            if possible in connections.columns:

                weight_column = possible
                break

        if weight_column is None:
            weight_column = "weight"

        source_column = None
        target_column = None

        possible_source_columns = [
            "bodyId_pre",
            "bodyId_source"
        ]

        possible_target_columns = [
            "bodyId_post",
            "bodyId_target"
        ]

        for column in possible_source_columns:

            if column in connections.columns:

                source_column = column
                break

        for column in possible_target_columns:

            if column in connections.columns:

                target_column = column
                break

        for _, neuron in neurons.iterrows():

            body_id = neuron.get(
                "bodyId",
                ""
            )

            neuron_type = neuron.get(
                "type",
                ""
            )

            instance = neuron.get(
                "instance",
                ""
            )

            weight = 0

            if weight_column in connections.columns:

                matches = None

                if direction == "upstream":

                    if target_column is not None:

                        matches = connections[
                            connections[target_column]
                            ==
                            body_id
                        ]

                else:

                    if source_column is not None:

                        matches = connections[
                            connections[source_column]
                            ==
                            body_id
                        ]

                if matches is not None and len(matches) > 0:

                    try:

                        weight = matches[
                            weight_column
                        ].sum()

                    except Exception:

                        weight = 0

            row = self.connections_table.rowCount()

            self.connections_table.insertRow(
                row
            )

            self.connections_table.setItem(
                row,
                0,
                QTableWidgetItem(
                    str(body_id)
                )
            )

            self.connections_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    str(neuron_type)
                )
            )

            self.connections_table.setItem(
                row,
                2,
                QTableWidgetItem(
                    str(instance)
                )
            )

            self.connections_table.setItem(
                row,
                3,
                QTableWidgetItem(
                    str(weight)
                )
            )

    def export_csv(self):

        if (
            self.current_dataframe is None
            or
            len(self.current_dataframe) == 0
        ):

            QMessageBox.information(
                self,
                "Export",
                "There is no search data to export."
            )

            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            "neurons.csv",
            "CSV Files (*.csv)"
        )

        if not filename:
            return

        try:

            self.current_dataframe.to_csv(
                filename,
                index=False
            )

            QMessageBox.information(
                self,
                "Export Complete",
                "CSV exported successfully."
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Export Error",
                str(error)
            )

    def export_json(self):

        if (
            self.current_dataframe is None
            or
            len(self.current_dataframe) == 0
        ):

            QMessageBox.information(
                self,
                "Export",
                "There is no search data to export."
            )

            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON",
            "neurons.json",
            "JSON Files (*.json)"
        )

        if not filename:
            return

        try:

            records = (
                self.current_dataframe
                .where(
                    self.current_dataframe.notna(),
                    None
                )
                .to_dict(
                    orient="records"
                )
            )

            with open(
                filename,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    records,
                    file,
                    indent=4,
                    default=str
                )

            QMessageBox.information(
                self,
                "Export Complete",
                "JSON exported successfully."
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Export Error",
                str(error)
            )

    def sign_out(self):

        answer = QMessageBox.question(
            self,
            "Sign Out",
            "Sign out of the current neuPrint session?"
        )

        if answer == QMessageBox.Yes:

            self.close()


def apply_styles(app):

    app.setStyleSheet("""

        QWidget {
            background-color: #151821;
            color: #eeeeee;
            font-family: "Segoe UI";
            font-size: 11pt;
        }

        QMainWindow {
            background-color: #151821;
        }

        #sidebar {
            background-color: #10131a;
            border-right: 1px solid #292d3a;
        }

        #logo {
            font-size: 44px;
            padding: 8px;
        }

        #sidebarTitle {
            font-size: 15pt;
            font-weight: bold;
            padding-bottom: 10px;
        }

        #brainButton {
            background-color: #202532;
            border: 1px solid #303647;
            border-radius: 7px;
            padding: 9px;
            text-align: left;
        }

        #brainButton:hover {
            background-color: #30394f;
        }

        #infoButton {
            background-color: #202532;
            border: 1px solid #303647;
            border-radius: 7px;
            font-weight: bold;
        }

        #infoButton:hover {
            background-color: #3d4a6b;
        }

        #mainTitle {
            font-size: 20pt;
            font-weight: bold;
        }

        #sectionTitle {
            font-size: 16pt;
            font-weight: bold;
            padding-bottom: 8px;
        }

        #subTitle {
            font-size: 13pt;
            font-weight: bold;
            padding-top: 4px;
        }

        #loginTitle {
            font-size: 22pt;
            font-weight: bold;
        }

        #loginSubtitle {
            color: #9fa7ba;
            padding-bottom: 10px;
        }

        #fieldLabel {
            font-weight: bold;
        }

        #smallText {
            color: #8f98ac;
        }

        #status {
            color: #8fb4ff;
            padding: 8px;
        }

        #connected {
            color: #70d68a;
            font-weight: bold;
        }

        #sandboxStatus {
            color: #70d68a;
            font-weight: bold;
            padding: 6px 12px;
        }

        #sandboxPanel {
            background-color: #181d28;
            border: 1px solid #303647;
            border-radius: 8px;
        }

        QLineEdit,
        QComboBox,
        QTextEdit,
        QTableWidget,
        QSpinBox {
            background-color: #1c202b;
            border: 1px solid #353b4c;
            border-radius: 7px;
            padding: 7px;
        }

        QLineEdit:focus,
        QComboBox:focus,
        QTextEdit:focus,
        QSpinBox:focus {
            border: 1px solid #647cff;
        }

        QPushButton {
            background-color: #252b3a;
            border: 1px solid #394155;
            border-radius: 7px;
            padding: 9px 14px;
        }

        QPushButton:hover {
            background-color: #343d55;
        }

        #primaryButton {
            background-color: #4d61d8;
            border: 1px solid #6679ee;
            font-weight: bold;
        }

        #primaryButton:hover {
            background-color: #6174eb;
        }

        QTabWidget::pane {
            border: 1px solid #303647;
            border-radius: 7px;
            background-color: #181c26;
        }

        QTabBar::tab {
            background-color: #202532;
            padding: 10px 15px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: #4d61d8;
        }

        QHeaderView::section {
            background-color: #252b3a;
            padding: 8px;
            border: none;
            font-weight: bold;
        }

        QTableWidget {
            gridline-color: #303647;
        }

        QCheckBox {
            spacing: 7px;
        }

        QProgressBar {
            background-color: #10141d;
            border: 1px solid #303647;
            border-radius: 5px;
        }

        QProgressBar::chunk {
            background-color: #4d61d8;
            border-radius: 4px;
        }

        QSlider::groove:horizontal {
            height: 5px;
            background: #303647;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
            background: #6679ee;
        }

    """)


def main():

    app = QApplication(
        sys.argv
    )

    apply_styles(
        app
    )

    login = LoginWindow()

    result = login.exec()

    if result != QDialog.Accepted:

        sys.exit(0)

    window = MainWindow(
        login.client
    )

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()