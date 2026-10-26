/*
 * Darksham OS login splash
 * DARKSHAM wipes in left to right, the sword drops into place,
 * then a metal shine runs down the blade.
 */
import QtQuick

Rectangle {
    id: root
    color: "#08080a"

    property int stage   // set by ksplash, not needed for the animation

    // logo source images are 850 x 775
    readonly property real logoScale: Math.min(height * 0.55 / 775, width * 0.42 / 850)

    Image {
        anchors.fill: parent
        source: "images/background.png"
        fillMode: Image.PreserveAspectCrop
        smooth: true
    }

    Item {
        id: logo
        width: 850 * root.logoScale
        height: 775 * root.logoScale
        anchors.centerIn: parent

        // 1) text, revealed by a growing clip
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

        // 3) the exact original logo replaces the pieces when the sword lands
        Image {
            id: full
            anchors.fill: parent
            source: "images/full.png"
            opacity: 0
            smooth: true; mipmap: true
        }

        // 2) sword, starts above the screen
        Item {
            id: swordBox
            width: logo.width; height: logo.height
            y: -root.height

            Image { id: swordImg; anchors.fill: parent; source: "images/sword.png"; smooth: true; mipmap: true }
            Image { id: flash; anchors.fill: parent; source: "images/sword_glow.png"; opacity: 0; smooth: true }

            // 4) shine: stacked light bands (wide+faint to narrow+bright)
            // gives a soft edge without shaders, so it works on any renderer
            property real shineY: -height * 0.2
            Repeater {
                model: [ { h: 0.26, o: 0.40 }, { h: 0.15, o: 0.60 }, { h: 0.06, o: 1.0 } ]
                Item {
                    required property var modelData
                    width: swordBox.width
                    height: swordBox.height * modelData.h
                    y: swordBox.shineY - height / 2
                    clip: true
                    opacity: modelData.o
                    Image {
                        width: swordBox.width; height: swordBox.height
                        y: -parent.y
                        source: "images/sword_shine.png"
                        smooth: true
                    }
                }
            }
        }
    }

    SequentialAnimation {
        running: true

        PauseAnimation { duration: 250 }
        NumberAnimation { target: textClip; property: "width"; to: logo.width; duration: 1100; easing.type: Easing.OutCubic }
        NumberAnimation { target: swordBox; property: "y"; to: 0; duration: 550; easing.type: Easing.InCubic }

        // landing: swap to the exact logo, flash, small shake
        ParallelAnimation {
            NumberAnimation { target: full; property: "opacity"; to: 1; duration: 120 }
            NumberAnimation { target: swordImg; property: "opacity"; to: 0; duration: 120 }
            SequentialAnimation {
                NumberAnimation { target: flash; property: "opacity"; to: 1; duration: 60 }
                NumberAnimation { target: flash; property: "opacity"; to: 0; duration: 320 }
            }
            SequentialAnimation {
                NumberAnimation { target: logo; property: "anchors.verticalCenterOffset"; to: 6; duration: 50 }
                NumberAnimation { target: logo; property: "anchors.verticalCenterOffset"; to: -4; duration: 70 }
                NumberAnimation { target: logo; property: "anchors.verticalCenterOffset"; to: 2; duration: 70 }
                NumberAnimation { target: logo; property: "anchors.verticalCenterOffset"; to: 0; duration: 80 }
            }
        }

        PauseAnimation { duration: 150 }
        NumberAnimation { target: swordBox; property: "shineY"; to: swordBox.height * 1.2; duration: 1300; easing.type: Easing.InOutSine }
    }
}
