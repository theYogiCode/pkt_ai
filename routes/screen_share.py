# This file manages WebRTC signaling for administrator
# screen sharing.
#
# The administrator's screen capture continues until the
# administrator stops it. Employees can reconnect to the
# same active share when moving between test questions.

from flask import request
from flask_socketio import emit


# Store the current screen-sharing state.
screen_share_active = False

# Store the administrator's SocketIO connection ID.
admin_sid = None


def register_screen_share_events(socketio):

    @socketio.on("start_screen_share")
    def start_screen_share():

        global screen_share_active
        global admin_sid

        # Remember the administrator who started sharing.
        admin_sid = request.sid

        # Keep the sharing state active.
        screen_share_active = True

        # Notify all connected employees.
        emit(
            "screen_share_started",
            broadcast=True
        )


    @socketio.on("stop_screen_share")
    def stop_screen_share():

        global screen_share_active
        global admin_sid

        # Stop the sharing state.
        screen_share_active = False

        admin_sid = None

        # Notify all employees.
        emit(
            "screen_share_stopped",
            broadcast=True
        )


    @socketio.on("check_screen_share")
    def check_screen_share():

        # Return the current sharing state.
        emit(
            "screen_share_status",
            {
                "active": screen_share_active
            }
        )


    @socketio.on("join_screen_share")
    def join_screen_share():

        # If no administrator is sharing,
        # the employee cannot join.
        if not screen_share_active or not admin_sid:

            emit(
                "screen_share_unavailable"
            )

            return


        # Tell the administrator that this browser
        # wants to receive the shared screen.
        emit(
            "viewer_joined",
            {
                "viewer_sid": request.sid
            },
            to=admin_sid
        )


    @socketio.on("offer")
    def handle_offer(data):

        # Forward the WebRTC offer from admin
        # to the employee.
        target_sid = data.get("target")

        if target_sid:

            emit(
                "offer",
                {
                    "offer": data.get("offer"),
                    "admin_sid": request.sid
                },
                to=target_sid
            )


    @socketio.on("answer")
    def handle_answer(data):

        # Forward the employee's answer
        # to the administrator.
        target_sid = data.get("target")

        if target_sid:

            emit(
                "answer",
                {
                    "answer": data.get("answer"),
                    "viewer_sid": request.sid
                },
                to=target_sid
            )


    @socketio.on("ice_candidate")
    def handle_ice_candidate(data):

        # Forward ICE candidates between
        # administrator and employee.
        target_sid = data.get("target")

        if target_sid:

            emit(
                "ice_candidate",
                {
                    "candidate": data.get("candidate"),
                    "sender_sid": request.sid
                },
                to=target_sid
            )