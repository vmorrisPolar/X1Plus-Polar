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
