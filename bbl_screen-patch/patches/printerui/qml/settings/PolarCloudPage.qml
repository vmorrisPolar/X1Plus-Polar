import QtQuick 2.12
import QtQuick.Controls 2.12
import UIBase 1.0
import QtQuick.Layouts 1.12
import Printer 1.0
import "qrc:/uibase/qml/widgets"
import "../X1Plus.js" as X1Plus

Item {
    id: polarCloudPage
    property string username: X1Plus.Settings.get("polar.username", "")
    property string pin: X1Plus.Settings.get("polar.pin", "")
    property bool cloudEnabled: X1Plus.Settings.get("polar.enabled", false)
    property string connectionState: X1Plus.Settings.get("polar.connect_state", "DISCONNECTED")
    property string errorMessage: X1Plus.Settings.get("polar.error", "")

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 32

        Text {
            text: qsTr("Polar Cloud Connection")
            font: Fonts.head_48
            color: Colors.brand
            horizontalAlignment: Text.AlignHCenter
            Layout.alignment: Qt.AlignHCenter
        }

        // Status indicator
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10
            
            Rectangle {
                width: 16
                height: 16
                radius: width/2
                color: {
                    switch(connectionState) {
                        case "ESTABLISHED": return "#20ce62" // Green
                        case "CONNECTING":
                        case "WAITING_HELLO": return "#ffd700" // Yellow
                        default: return "#ff4444" // Red
                    }
                }
            }

            Text {
                text: {
                    if (!cloudEnabled) return qsTr("Disabled")
                    switch(connectionState) {
                        case "ESTABLISHED": return qsTr("Connected")
                        case "CONNECTING": return qsTr("Connecting...")
                        case "WAITING_HELLO": return qsTr("Authenticating...")
                        default:
                            return errorMessage ? qsTr("Error: ") + errorMessage : qsTr("Disconnected")
                    }
                }
                font: Fonts.body_28
                color: Colors.gray_200
            }
        }

        TextField {
            id: usernameField
            placeholderText: qsTr("Username (email)")
            text: polarCloudPage.username
            onTextChanged: polarCloudPage.username = text
            width: 400
            font: Fonts.body_28
        }

        TextField {
            id: pinField
            placeholderText: qsTr("PIN (numerical)")
            inputMethodHints: Qt.ImhDigitsOnly
            text: polarCloudPage.pin
            onTextChanged: polarCloudPage.pin = text
            width: 400
            font: Fonts.body_28
        }

        RowLayout {
            spacing: 16
            Switch {
                id: cloudSwitch
                checked: polarCloudPage.cloudEnabled
                onCheckedChanged: {
                    polarCloudPage.cloudEnabled = checked;
                    X1Plus.Settings.put("polar.enabled", checked);
                    X1Plus.Settings.put("polar.username", usernameField.text);
                    X1Plus.Settings.put("polar.pin", pinField.text);
                }
            }
            Text {
                text: qsTr("Enable Polar Cloud Connection")
                font: Fonts.body_28
                color: Colors.gray_200
            }
        }
    }

    X1PBackButton {
        onClicked: { 
            pageStack.pop()
        }
    }
}
