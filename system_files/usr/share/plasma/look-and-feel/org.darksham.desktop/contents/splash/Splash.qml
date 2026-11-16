/*
 * Darksham OS login splash
 * The DARKSHAM wordmark wipes in from left to right, then settles with a soft pulse.
 */
import QtQuick

Rectangle {
    id: root
    color: "#08080a"

    property int stage   // set by ksplash, not needed for the animation

    // wordmark source image is 850 x 137
    readonly property real logoScale: Math.min(width * 0.42 / 850, height * 0.5 / 137)

    Image {
        anchors.fill: parent
        source: "images/background.png"
        fillMode: Image.PreserveAspectCrop
        smooth: true
    }

    Item {
        id: logo
        width: 850 * root.logoScale
        height: 137 * root.logoScale
        anchors.centerIn: parent

        // text, revealed by a growing clip
        Item {
            id: textClip
            width: 0
            height: parent.height
            clip: true
            Image {
                width: logo.width; height: logo.height
                source: "images/text.png"
                smooth: true; mipmap: true
            }
        }
    }

    SequentialAnimation {
        running: true

        PauseAnimation { duration: 250 }
        NumberAnimation { target: textClip; property: "width"; to: logo.width; duration: 1100; easing.type: Easing.OutCubic }

        // settle: tiny scale pulse
        NumberAnimation { target: logo; property: "scale"; to: 1.03; duration: 160; easing.type: Easing.OutQuad }
        NumberAnimation { target: logo; property: "scale"; to: 1.0; duration: 260; easing.type: Easing.InOutQuad }
    }
}
