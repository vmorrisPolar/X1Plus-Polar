import QtQuick 2.12
import QtQuick.Controls 2.5
import UIBase 1.0

Text {
    property real maxWidth: 0

    font: Fonts.body_24

    onMaxWidthChanged: {
        if (maxWidth > 0 && fontSizeMode !== Text.HorizontalFit) {
            width = Math.min(implicitWidth, maxWidth)
            if (width < implicitWidth) {
                fontSizeMode = Text.HorizontalFit
            }
        }
    }

    onImplicitWidthChanged: {
        if (maxWidth > 0 && fontSizeMode !== Text.HorizontalFit) {
            width = Math.min(implicitWidth, maxWidth)
            if (width < implicitWidth) {
                fontSizeMode = Text.HorizontalFit
            }
        }
    }
}
