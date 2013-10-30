import QtQuick 1.1

ListView {
    signal tariff_changed ( variant tariff )

    function set_tariffs(tariffs) {
        model.clear()
        for(var i=0; i<tariffs.length;i++) {
            var tariff = tariffs[i]
            model.append({ title: tariff.name, tariff: tariff  })
        }
    }

    id: widget
    anchors.fill: parent

    width: 700
    height: 65

    model: ListModel {
        id: model
    }

    onCurrentIndexChanged: {
        tariff_changed(model.get(currentIndex).tariff)
    }

    highlightFollowsCurrentItem: true
    highlightMoveDuration: 500
    highlight: Component {
        Rectangle {
            color: "lightsteelblue"
            radius: 15
            y: widget.currentItem.y
        }
    }
    focus: true

    delegate: Rectangle {
        id: rect

        color: "transparent"
        height: parent.height
        width: text.width + 50
        radius: 15

        MouseArea {
            anchors.fill: parent
            onClicked: {
                widget.currentIndex = index
            }
        }

        border.color: "black"
        border.width: 1


        Text {
            id: text
            text: title
            font.pointSize: 22

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    orientation: ListView.Horizontal

}