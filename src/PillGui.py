from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path


WINDOW = None


class PillWindow(QtWidgets.QMainWindow):
    def __init__(self, tool, parent=None):
        super().__init__()
        self.event_loop = None
        self.tool = tool
        self.qapp = parent
        self.title = "RAPT Pill To Mead Tools"
        self.parent = parent
        self.name = self.title
        self.setObjectName(self.name)
        self.pill_widgets = []
        self.resize(800, 500)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.Window)

        self.setStyleSheet(self.tool.curr_dir.joinpath("stylesheet/darkorange.css").read_text())
        self.icon = QtGui.QPixmap(self.tool.curr_dir.joinpath("icons/meadtools-pill.png").as_posix()).scaledToWidth(32)
        self.setWindowIcon(self.icon)
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.setCentralWidget(self.main_widget)
        self.main_widget.setLayout(self.main_layout)
        self.setWindowTitle(self.title)

        self.settings = QtCore.QSettings("RaptPillTracker", self.name.replace(" ", "_"))
        if self.settings:
            self.restoreGeometry(self.settings.value("geometry"))
        else:
            self.resize(500, 500)

        self.log_viewer = LogViewer(self.tool.log_file)

        # layouts
        self.hlay_MTLogin = QtWidgets.QHBoxLayout()
        self.hlay_auth = QtWidgets.QHBoxLayout()

        # MTLogin
        self.cframe_mtools = CollapsibleFrame("MeadTools Login Details", "vertical", True, self)
        self.rbtngrp = QtWidgets.QButtonGroup()
        self.rbtn_mtUser = QtWidgets.QRadioButton("MeadTools User")
        self.rbtn_google = QtWidgets.QRadioButton("Google Auth")
        self.rbtngrp.addButton(self.rbtn_mtUser)
        self.rbtngrp.setId(self.rbtn_mtUser, 0)
        self.rbtngrp.addButton(self.rbtn_google)
        self.rbtngrp.setId(self.rbtn_google, 1)
        self.rbtn_mtUser.setChecked(True)

        self.lablineE_googleAuth = LabeledLineEdit("Google Email:", "", False, self)
        self.lablineE_googleAuth.setVisible(False)
        self.lablineE_username = LabeledLineEdit("Mead Tools Email:", "", False, self)
        self.lablineE_password = LabeledLineEdit("Mead Tools Password:", "", False, self)
        self.lablineE_password.lineEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        self.pbtn_login = QtWidgets.QPushButton("Login")
        self.pbtn_log = QtWidgets.QPushButton("View Log")

        self.hlay_auth.addWidget(self.rbtn_mtUser)
        self.hlay_auth.addWidget(self.rbtn_google)
        self.hlay_auth.addWidget(self.pbtn_log)

        self.hlay_MTLogin.addWidget(self.lablineE_username)
        self.hlay_MTLogin.addWidget(self.lablineE_password)
        self.hlay_MTLogin.addWidget(self.pbtn_login)
        self.cframe_mtools.add_layout(self.hlay_auth)
        self.cframe_mtools.add_widget(self.lablineE_googleAuth)
        self.cframe_mtools.add_layout(self.hlay_MTLogin)

        self.pbtn_addBrew = QtWidgets.QPushButton("Add new Brew")
        # scroll area to hold pill data
        self.sArea_pills = setup_scrollArea("sArea_pills", True, self)

        self.pbtn_startBrews = QtWidgets.QPushButton("Start all brews")
        self.statusbar = QtWidgets.QStatusBar()

        # Final UI Comp
        self.main_layout.addWidget(self.cframe_mtools)
        self.main_layout.addWidget(self.pbtn_addBrew)
        self.main_layout.addWidget(self.sArea_pills)
        self.main_layout.addWidget(self.pbtn_startBrews)

        self.main_layout.addWidget(self.statusbar)

        self.load_last_data()
        self.connect_ui()
        self.logged_in(False)

    @property
    def data(self):
        return self.tool.data

    @property
    def mdata(self):
        return self.data.get("MTDetails", {})

    @property
    def mtools(self):
        return self.tool.mtools

    def load_last_data(self):
        """load the last used data in the gui"""
        if username := self.mdata.get("MTEmail", None):
            self.lablineE_username.set_text(username)
        if password := self.mdata.get("MTPassword", None):
            self.lablineE_password.set_text(password)

        if len(self.data.get("Sessions", [])):
            for session in self.data.get("Sessions", []):
                self.tool.log_event("Loading session data")
                frame_holder = CollapsibleFrame(
                    session.get("BrewName", "BrewNameNot Set"), start_opened=True, parent=self
                )
                widget = PillWidget(session, frame_holder, self)
                frame_holder.add_widget(widget)
                self.pill_widgets.append(widget)
                self.sArea_pills.widget().layout().addWidget(frame_holder)

        self.lablineE_googleAuth.set_text(self.mdata.get("Google", ""))

        if auth := self.settings.value("auth_type"):
            if auth == 0:
                self.rbtn_mtUser.setChecked(True)
                self.lablineE_googleAuth.setVisible(False)
                self.lablineE_username.setVisible(True)
                self.lablineE_password.setVisible(True)
            else:
                self.rbtn_google.setChecked(True)
                self.lablineE_googleAuth.setVisible(True)
                self.lablineE_username.setVisible(False)
                self.lablineE_password.setVisible(False)
                self.lablineE_googleAuth.set_text(self.mdata.get("Google", ""))

    def connect_ui(self):
        self.pbtn_login.clicked.connect(self.login_to_meadtools)
        self.pbtn_addBrew.clicked.connect(self.add_brew)
        self.pbtn_startBrews.clicked.connect(self.start_brews)
        self.rbtngrp.buttonClicked.connect(self.update_auth_input)
        self.pbtn_log.clicked.connect(self.show_log)

    def update_auth_input(self, button):
        if button.text() == "MeadTools User":
            self.lablineE_googleAuth.setVisible(False)
            self.lablineE_username.setVisible(True)
            self.lablineE_password.setVisible(True)
        else:
            self.lablineE_googleAuth.setVisible(True)
            self.lablineE_username.setVisible(False)
            self.lablineE_password.setVisible(False)

    def add_brew(self):
        frame_holder = CollapsibleFrame("BrewName", start_opened=True, parent=self)
        data = {}
        self.tool.data.get("Sessions", []).append(data)
        widget = PillWidget(data, frame_holder, self)
        frame_holder.add_widget(widget)
        self.pill_widgets.append(widget)
        self.sArea_pills.widget().layout().addWidget(frame_holder)

    def show_log(self):
        self.log_viewer.show()

    def start_brews(self):
        # save all data to the data.json then run pills
        if self.is_shift_pressed():
            self.tool.log_to_db = False

        for pill in self.pill_widgets:
            pill.save_data()
            pill.start_session()
        self.update_status("Starting all pill sessions...")

    def login_to_meadtools(self):
        """attempt to login to meadtools"""
        if self.rbtngrp.checkedId() == 0:
            self.tool.data["MTDetails"]["MTEmail"] = self.lablineE_username.text
            self.tool.data["MTDetails"]["MTPassword"] = self.lablineE_password.text
            self.tool.mtools.save_data()
            success = self.tool.mtools.handle_login()
            if success:
                self.update_status("Successfully Logged into Mead Tools")
                self.mdata["LoginType"] = "MeadTools"
            else:
                self.update_status("Failed to Login to Mead Tools")
                self.mdata["LoginType"] = "None"
        else:
            result = self.yes_no_messagebox(
                "Would you like to continue?",
                "This will try to authenticate with Google to login to Mead Tools.<br><br>"
                "This may open a browser for you to complete the login (if you haven't done it before).<br><br>Are you sure you want to continue?",
            )
            if not result:
                return
            self.tool.data["MTDetails"]["Google"] = self.lablineE_googleAuth.text
            self.tool.mtools.save_data()
            success = self.tool.mtools.google_auth()
            if success:
                self.update_status("Successfully Logged into Mead Tools with Google...")
                self.mdata["LoginType"] = "Google"

            else:
                self.mdata["LoginType"] = "None"
                self.update_status("Failed to Login to Mead Tools via Google...")

    def update_status(self, message: str):
        """set a message in the statusbar and disappear after 5 seconds

        Args:
            message (str): message to display
        """
        self.statusbar.showMessage(message, 10000)

    def closeEvent(self, event):
        # save the window settings
        if self.settings:
            geo = self.saveGeometry()
            self.settings.setValue("geometry", geo)
            self.settings.setValue("auth_type", self.rbtngrp.checkedId())
        if self.log_viewer:
            self.log_viewer.close()

    def yes_no_messagebox(self, title: str, msg: str, icon_name: str = "NoIcon"):
        """Create yes/no message box with given title and message

        Args:
            title (str): title of msgbox
            msg (str): message to display to user
            icon_name (str, optional): icon type for window. Defaults to "NoIcon". - Information, Warning, Error, Critical, NoIcon
        """
        msg_box = QtWidgets.QMessageBox(self)
        if icon_name == "Information":
            msg_box.setIcon(QtWidgets.QMessageBox.Information)
        elif icon_name == "Warning":
            msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        elif icon_name == "Error":
            msg_box.setIcon(QtWidgets.QMessageBox.Error)
        elif icon_name == "Critical":
            msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        elif icon_name == "NoIcon":
            msg_box.setIcon(QtWidgets.QMessageBox.NoIcon)

        msg_box.setText(msg)
        msg_box.setWindowTitle(title)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        return_value = msg_box.exec()
        if return_value == QtWidgets.QMessageBox.Yes:
            return True
        elif return_value == QtWidgets.QMessageBox.No:
            return False
        return None

    def logged_in(self, can_start: bool):
        """Set the buttons on or off if we are logged in

        Args:
            can_start (bool): whether we can login or not
        """
        self.tool.log_event(f"LoggedIn: {can_start}")
        self.pbtn_addBrew.setEnabled(can_start)
        self.pbtn_startBrews.setEnabled(can_start)
        for brew in self.pill_widgets:
            brew.toggle_start_brew(can_start)
            brew.toggle_gen_token(can_start)

    def update_huds(self, pill):
        for item in self.pill_widgets:
            if item.brew_name == pill.session_name and item.mac_address == pill.mac_address:
                self.tool.log_event(f"Updating HUD: {item.brew_name}")
                item.update_hud(pill)

    def is_shift_pressed(self):
        """Handy function to determine if the shift key is pressed
        Returns:
            bool: True if the shift key is pressed, False otherwise
        """
        return QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier


class LabeledLineEdit(QtWidgets.QWidget):
    def __init__(self, label_text: str, text: str, label_above: bool = False, parent=None):
        "Labeled LineEdit for easier setup"
        super().__init__(parent=parent)
        self.layout = None
        if label_above:
            self.layout = QtWidgets.QVBoxLayout()
        else:
            self.layout = QtWidgets.QHBoxLayout()
        self.lab_title = QtWidgets.QLabel(label_text)
        self.lineEdit = QtWidgets.QLineEdit(text)
        self.setLayout(self.layout)
        self.layout.addWidget(self.lab_title)
        self.layout.addWidget(self.lineEdit)

    @property
    def text(self):
        return self.lineEdit.text()

    def update_label(self, label):
        self.lab_title.setText(label)

    def set_text(self, text):
        self.lineEdit.setText(str(text))


class PillWidget(QtWidgets.QWidget):
    def __init__(self, session_data: dict, frame, ui):
        super().__init__(parent=ui)
        self.running = False
        self.ui = ui
        self.frame = frame
        self.data = session_data

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.setLayout(self.main_layout)

        self.hlay_hud = QtWidgets.QHBoxLayout()
        self.hlay_hud.setAlignment(QtCore.Qt.AlignLeft)
        self.hlay_deviceToken = QtWidgets.QHBoxLayout()

        self.pbtn_remove = QtWidgets.QPushButton(" X ")
        self.pbtn_remove.setToolTip("Remove the current brew data")
        self.pbtn_remove.setMaximumWidth(50)

        self.lab_sg = QtWidgets.QLabel("SG: ")
        self.lab_sg.setObjectName("HUDLabel")

        self.lab_sgValue = QtWidgets.QLabel("0")
        self.lab_sgValue.setObjectName("HUD")

        self.lab_abv = QtWidgets.QLabel("ABV: ")
        self.lab_abv.setObjectName("HUDLabel")

        self.lab_abvValue = QtWidgets.QLabel("0")
        self.lab_abvValue.setObjectName("HUD")

        self.lab_lastTime = QtWidgets.QLabel("Last Time: ")
        self.lab_lastTime.setObjectName("HUDLabel")

        self.lab_lastTimeValue = QtWidgets.QLabel("None")
        self.lab_lastTimeValue.setObjectName("HUD")

        self.hlay_hud.addWidget(self.lab_sg)
        self.hlay_hud.addWidget(self.lab_sgValue)
        self.hlay_hud.addWidget(self.lab_abv)
        self.hlay_hud.addWidget(self.lab_abvValue)
        self.hlay_hud.addWidget(self.lab_lastTime)
        self.hlay_hud.addWidget(self.lab_lastTimeValue)

        self.labLineE_deviceToken = LabeledLineEdit("iSpindel Device Token:", "", False, self)
        self.pbtn_genToken = QtWidgets.QPushButton("Generate Device Token")
        self.hlay_deviceToken.addWidget(self.labLineE_deviceToken)
        self.hlay_deviceToken.addWidget(self.pbtn_genToken)

        self.labLineE_recipeId = LabeledLineEdit("Recipe ID:", "", False, self)
        self.labLineE_brewName = LabeledLineEdit("Brew Name:", "", False, self)
        self.labLineE_name = LabeledLineEdit("Pill Name:", "", False, self)
        self.labLineE_macAddress = LabeledLineEdit("Pill MAC Address:", "", False, self)
        self.labLineE_pollInterval = LabeledLineEdit("Poll Interval:", "", False, self)

        self.chkbox_tempUnit = QtWidgets.QCheckBox("Temp in C?")
        self.chkbox_tempUnit.setChecked(True)

        self.pbtn_start_session = QtWidgets.QPushButton("Start Session")
        self.pbtn_start_session.setEnabled(self.ui.mtools.logged_in)

        self.main_layout.addWidget(self.pbtn_remove)
        self.main_layout.addLayout(self.hlay_hud)
        self.main_layout.addLayout(self.hlay_deviceToken)
        self.main_layout.addWidget(self.labLineE_name)
        self.main_layout.addWidget(self.labLineE_recipeId)
        self.main_layout.addWidget(self.labLineE_brewName)
        self.main_layout.addWidget(self.labLineE_macAddress)
        self.main_layout.addWidget(self.labLineE_pollInterval)
        self.main_layout.addWidget(self.chkbox_tempUnit)
        self.main_layout.addWidget(self.pbtn_start_session)
        self.load_data()
        self.connect_ui()

    @property
    def brew_name(self):
        return self.labLineE_brewName.text

    @property
    def mac_address(self):
        return self.labLineE_macAddress.text

    @property
    def json(self):
        repr = {
            "BrewName": "",
            "Pill Name": "",
            "Mac Address": "",
            "Poll Interval": "",
            "Temp in C": False,
            "MTRecipeId": -1,
        }
        repr["BrewName"] = self.labLineE_brewName.text
        repr["Pill Name"] = self.labLineE_name.text
        repr["Mac Address"] = self.labLineE_macAddress.text
        repr["Poll Interval"] = self.labLineE_pollInterval.text
        repr["Temp in C"] = self.chkbox_tempUnit.isChecked()
        repr["MTRecipeId"] = int(self.labLineE_recipeId.text)
        return repr

    def connect_ui(self):
        """Connect ui to signals and set tab order"""
        self.setTabOrder(self.labLineE_deviceToken.lineEdit, self.labLineE_name.lineEdit)
        self.setTabOrder(self.labLineE_name.lineEdit, self.labLineE_recipeId.lineEdit)
        self.setTabOrder(self.labLineE_recipeId.lineEdit, self.labLineE_brewName.lineEdit)
        self.setTabOrder(self.labLineE_brewName.lineEdit, self.labLineE_macAddress.lineEdit)
        self.setTabOrder(self.labLineE_macAddress.lineEdit, self.labLineE_pollInterval.lineEdit)
        self.setTabOrder(self.labLineE_pollInterval.lineEdit, self.chkbox_tempUnit)

        self.pbtn_genToken.clicked.connect(self.generate_token)
        self.pbtn_remove.clicked.connect(self.remove_pill)
        self.labLineE_brewName.lineEdit.editingFinished.connect(self.set_brew_name)
        self.labLineE_deviceToken.lineEdit.editingFinished.connect(self.save_data)
        self.labLineE_macAddress.lineEdit.editingFinished.connect(self.save_data)
        self.labLineE_name.lineEdit.editingFinished.connect(self.save_data)
        self.labLineE_pollInterval.lineEdit.editingFinished.connect(self.save_data)
        self.labLineE_recipeId.lineEdit.editingFinished.connect(self.save_data)
        self.pbtn_start_session.clicked.connect(self.start_session)
        self.chkbox_tempUnit.checkStateChanged.connect(self.save_data)

    def update_hud(self, pill):
        self.lab_sgValue.setText(f" {pill.curr_gravity}")
        self.lab_abvValue.setText(str(pill.abv))
        self.lab_lastTimeValue.setText(str(pill.last_event))

    def toggle_gen_token(self, can_gen: bool):
        """Set whether the generate token button can be clicked

        Args:
            can_gen (bool): button can be clicked
        """
        self.pbtn_genToken.setEnabled(can_gen)

    def toggle_start_brew(self, can_start: bool):
        """Enable/Disable the start brew button based on if we are logged in

        Args:
            can_start (bool): logged in or not
        """
        self.pbtn_genToken.setEnabled(not can_start)
        self.pbtn_start_session.setEnabled(can_start)

    def remove_pill(self):
        """Remove pill data and widget"""
        self.setParent(None)
        self.ui.tool.log_event(f"Removing Pill: {self.labLineE_brewName.text}")
        self.ui.pill_widgets.remove(self)
        self.frame.setParent(None)
        self.ui.tool.data.get("Sessions", []).remove(self.json)
        self.ui.mtools.save_data()

    def generate_token(self):
        token = self.ui.tool.mtools.generate_device_token()
        self.ui.tool.log_event(f"Generated new Token :{token}")
        self.ui.tool.data.get("MTDetails", {})["MTDeviceToken"] = token
        self.save_data()
        self.load_data()

    def set_device_token(self):
        self.save_data()

    def set_brew_name(self):
        brew_name = self.labLineE_brewName.text.rstrip()
        self.data["BrewName"] = brew_name
        self.frame.set_label(brew_name)
        self.labLineE_brewName.set_text(brew_name)
        self.save_data()

    def start_session(self):
        """Start the session(s)"""
        self.running = not self.running
        if self.running:
            self.pbtn_start_session.setText("Stop Session")
            self.ui.tool.run_pill(self.data)
            self.ui.update_status(f"Starting Session: {self.data.get('BrewName', 'UnSet Brew Name')}")
        else:
            self.pbtn_start_session.setText("Start Session")
            self.ui.update_status(f"Stopping Session: {self.data.get('BrewName', 'UnSet Brew Name')}")
            self.ui.tool.stop_pill(self.data)

    def load_data(self):
        self.labLineE_brewName.set_text(self.data.get("BrewName", ""))
        self.labLineE_name.set_text(self.data.get("Pill Name", ""))
        self.labLineE_deviceToken.set_text(self.ui.tool.data.get("MTDetails", {}).get("MTDeviceToken", None))
        self.labLineE_macAddress.set_text(self.data.get("Mac Address", None))
        self.labLineE_recipeId.set_text(self.data.get("MTRecipeId", -1))
        self.labLineE_pollInterval.set_text(self.data.get("Poll Interval", 120))
        self.chkbox_tempUnit.setChecked(self.data.get("Temp in C", False))

    def save_data(self):
        """Save widget data to json data and disk"""
        self.data["BrewName"] = self.labLineE_brewName.text
        self.data["Pill Name"] = self.labLineE_name.text
        self.data["Mac Address"] = self.labLineE_macAddress.text
        self.data["Poll Interval"] = self.labLineE_pollInterval.text
        self.data["Temp in C"] = self.chkbox_tempUnit.isChecked()
        self.data["MTRecipeId"] = int(self.labLineE_recipeId.text)
        self.ui.update_status("Saving Brew Data...")
        self.ui.tool.mtools.save_data()


class CollapsibleFrame(QtWidgets.QWidget):
    """Creates a button with a label to the right of it that can be used to
    hide/show widgets when the button is clicked. Can easily add layouts or widgets
    via the add_widget/add_layout methods
    E.g.
      | > | MyLabel
      --------------------------------
      Frame that contains widgets
    """

    def __init__(
        self,
        label_name: str,
        layout_orientation: str = "vertical",
        start_opened: bool = False,
        parent=None,
    ):
        """
        Setup a collapsible frame with a label

        Args:
            label_name (str): label for this frame
            layout_orientation (str, optional): should the layout be vertical or horizontal. Defaults to "vertical".
            start_opened (bool, optional): should the frame be opened on default. Defaults to False.
            parent (QtWidgets.QWidget, optional): Widget to parent to. Defaults to None.
        """
        super().__init__(parent=parent)
        self.arrow_right = "\u2b9e"
        self.arrow_down = "\u2b9f"
        self.frame_container = QtWidgets.QFrame()
        self.frame_container.setObjectName("Collapsed")
        self.frame_container.setStyleSheet(
            "#Collapsed {"
            "border-width: 1;"
            "border-radius: 3;"
            "border-style: solid;"
            "border-color: rgb(10, 10, 10)}"
        )

        self.lay_main = QtWidgets.QVBoxLayout()
        self.lay_main.setAlignment(QtCore.Qt.AlignRight)

        self.setLayout(self.lay_main)
        if layout_orientation == "vertical":
            self.layout_frame = QtWidgets.QVBoxLayout()
        elif layout_orientation == "horizontal":
            self.layout_frame = QtWidgets.QHBoxLayout()
        else:
            print("Invalid orientation, using Vertical")
            self.layout_frame = QtWidgets.QVBoxLayout()

        self.frame_container.setLayout(self.layout_frame)

        # for the button and label to live in
        self.hlay_outter = QtWidgets.QHBoxLayout()
        self.pbtn_toggle = QtWidgets.QPushButton(self.arrow_right)
        self.pbtn_toggle.setCheckable(True)
        self.pbtn_toggle.setStyleSheet("min-width:50px;margin:0px;padding:0px;min-height:30px")

        self.lab_title = QtWidgets.QLabel(label_name)
        self.hlay_outter.addWidget(self.pbtn_toggle, 0)
        self.hlay_outter.addWidget(self.lab_title, 2)

        self.lay_main.addLayout(self.hlay_outter)
        self.lay_main.addWidget(self.frame_container)
        if start_opened:
            self.pbtn_toggle.setChecked(True)
            self.toggle_collapse()

        self.connect_ui()

    def connect_ui(self):
        """Connect the ui to functions"""
        self.pbtn_toggle.clicked.connect(self.toggle_collapse)

    def set_label(self, label: str):
        """
        Set the label of the frame

        Args:
            label (str): label text
        """
        self.lab_title.setText(label)

    def toggle_collapse(self):
        """
        Toggle the collapse function of the frame. If it was collapsed, show it, else if it was visible, collapse it
        """
        if self.pbtn_toggle.isChecked():
            self.frame_container.setVisible(True)
            self.pbtn_toggle.setText(self.arrow_down)
        else:
            self.frame_container.setVisible(False)
            self.pbtn_toggle.setText(self.arrow_right)

    def add_widget(self, widget: QtWidgets.QWidget):
        """
        Add a widget to the frame

        Args:
            widget (QtWidgets.QWidget): Widget to add
        """
        self.layout_frame.addWidget(widget)

    def add_layout(self, layout: QtWidgets.QLayout):
        """
        Add a layout to the frame

        Args:
            layout (QtWidgets.QLayout): Layout to add
        """
        self.layout_frame.addLayout(layout)


class LogViewer(QtWidgets.QWidget):
    def __init__(self, log_path: Path):
        super().__init__()
        self.log_path = log_path
        self.last_size = 0

        self.setWindowTitle("Log Viewer")
        self.resize(600, 400)

        self.text_box = QtWidgets.QTextEdit(self)
        self.text_box.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.text_box)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_for_update)
        self.timer.start(1000)  # check every 1 second

        self.check_for_update()  # load initial content

    def check_for_update(self):
        if not self.log_path.exists():
            self.text_box.setPlainText("Log file does not exist.")
            return

        current_size = self.log_path.stat().st_size
        if current_size != self.last_size:
            self.last_size = current_size
            with self.log_path.open("r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            self.update_log_display(lines)

    def update_log_display(self, lines):
        self.text_box.clear()
        for line in lines:
            html_line = line.strip()

            html_line = html_line.replace("ERROR", "<span style='color:red; font-weight:bold'>ERROR</span>")
            html_line = html_line.replace("WARNING", "<span style='color:yellow; font-weight:bold'>WARNING</span>")
            html_line = html_line.replace("INFO", "<span style='color:green; font-weight:bold'>INFO</span>")
            # handle the data output
            html_line = html_line.replace("BrewName:", "<span style='color:orange; font-weight:bold'>BrewName:</span>")
            html_line = html_line.replace(
                "Firmware Version:", "<span style='color:orange; font-weight:bold'>Firmware Version:</span>"
            )
            html_line = html_line.replace("MacAddr:", "<span style='color:orange; font-weight:bold'>MacAddr:</span>")
            html_line = html_line.replace(
                "Start Gravity:", "<span style='color:orange; font-weight:bold'>Start Gravity:</span>"
            )
            html_line = html_line.replace(
                "CurrGravity:", "<span style='color:orange; font-weight:bold'>CurrGravity:</span>"
            )
            html_line = html_line.replace("ABV:", "<span style='color:orange; font-weight:bold'>ABV:</span>")
            html_line = html_line.replace(
                "Last Event TimeStamp:", "<span style='color:orange; font-weight:bold'>Last Event TimeStamp:</span>"
            )
            html_line = html_line.replace("Temp:", "<span style='color:orange; font-weight:bold'>Temp:</span>")
            html_line = html_line.replace("X-Accel :", "<span style='color:orange; font-weight:bold'>X-Accel :</span>")
            html_line = html_line.replace("Y-Accel :", "<span style='color:orange; font-weight:bold'>Y-Accel :</span>")
            html_line = html_line.replace("Z-Accel :", "<span style='color:orange; font-weight:bold'>Z-Accel :</span>")
            html_line = html_line.replace("Battery :", "<span style='color:orange; font-weight:bold'>Battery :</span>")

            self.text_box.insertHtml(f"{html_line}<br>")

        self.text_box.moveCursor(QtGui.QTextCursor.End)

    # def update_log_display(self, lines):
    #     self.text_box.clear()
    #     for line in lines:
    #         color = "yellow"
    #         if "ERROR" in line:
    #             color = "red"
    #         elif "WARNING" in line:
    #             color = "orange"
    #         elif "INFO" in line:
    #             color = "green"
    #         elif:
    #             "BrewName"

    #         html_line = f"<span style='color:{color}'>{line.strip()}</span><br>"
    #         self.text_box.insertHtml(html_line)

    #     self.text_box.moveCursor(QtGui.QTextCursor.End)


# ScrollArea Setup
def setup_scrollArea(name, is_vertical=True, parent=None):
    # setup all the inventory scrollarea stuff
    scroll_panel = QtWidgets.QWidget(parent=parent)
    scroll_area = QtWidgets.QScrollArea()
    scroll_area.setObjectName(name)
    scroll_area.setWidgetResizable(True)

    if is_vertical:
        scroll_layout = QtWidgets.QVBoxLayout()
        scroll_layout.setAlignment(QtCore.Qt.AlignTop)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    else:
        scroll_layout = QtWidgets.QHBoxLayout()
        scroll_layout.setAlignment(QtCore.Qt.AlignLeft)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    scroll_panel.setLayout(scroll_layout)
    scroll_area.setWidget(scroll_panel)

    return scroll_area


def setup_ui(data):
    global WINDOW
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication([])
    else:
        app = QtWidgets.QApplication.instance()
    app.setQuitOnLastWindowClosed(True)
    WINDOW = PillWindow(data, parent=app)
    WINDOW.show()
