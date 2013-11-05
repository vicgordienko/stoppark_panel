import QtQuick 1.1
import Qt.labs.gestures 1.0

Rectangle {
    id: widget

    width: 700
    height: 300

    property variant ticket
    signal new_payment (variant payment)

    function set_tariffs(tariffs) {
        var index = list.currentIndex
        model.clear()
        for(var i=0; i<tariffs.length;i++) {
            var tariff = tariffs[i]
            model.append({
                tariff: tariff,
                payment: ticket ? ticket.pay(tariff) : null
            })
        }
        list.currentIndex = index
    }

    function emit_current_payment() {
        if(list.currentIndex != -1) {
            var item = model.get(list.currentIndex)
            new_payment(item.payment)
        } else {
            new_payment(null)
        }
    }

    onTicketChanged: {
        for(var i=0; i<model.count; i++) {
            var item = model.get(i)
            model.setProperty(i, 'payment', ticket ? ticket.pay(item.tariff) : null)
        }
        emit_current_payment()
    }

    /*Rectangle {
        anchors.top: list.bottom
        anchors.topMargin: 7
        anchors.horizontalCenter: parent.horizontalCenter

        height: parent.height - list.height - 10
        width: parent.width - 5

        radius: 10
        border.width: 1
        border.color: "black"

        Behavior on color {
            ColorAnimation {
                duration: 500
            }
        }

        property variant item: list.currentIndex != -1 ? model.get(list.currentIndex) : null

        onItemChanged: {
            title.text = item ? item.tariff.title : ''
            if(item && item.payment && item.payment.enabled) {
                price_prefix.text = 'К оплате: '
                price.text = item.payment.price + ' грн.'
                color = 'lightgreen'
            } else {
                price_prefix.text = ''
                price.text = ''
                color = '#ff0c0c'
            }
        }

        MouseArea {
                anchors.fill: parent
                onClicked: {
                    list.positionViewAtIndex(list.currentIndex, ListView.Center)
                }
            }

        Text {
            id: title
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            font.pointSize: 22
        }

        Text {
            id: price_prefix
            anchors.right: price.left
            anchors.verticalCenter: parent.verticalCenter
            font.pointSize: 20
        }

        Text {
            id: price
             anchors.right: parent.right
             anchors.verticalCenter: parent.verticalCenter
             font.pointSize: 24
        }
    }*/

    ListView {
        id: list
        anchors.top: parent.top
        width: parent.width - 5

        height: parent.height - 5

        clip: true
        focus: true
        orientation: ListView.Vertical

        model: ListModel {
              id: model
        }

        onCurrentIndexChanged: {
            console.log('onCurrentIndexChanged', currentIndex)
            emit_current_payment()
        }

        highlightMoveDuration: 500
        /*highlightFollowsCurrentItem: false
        highlight: Rectangle {
            color: "lightsteelblue"
            radius: list.currentItem ? list.currentItem.radius: 0
            width: list.currentItem ? list.currentItem.width: 0
            height: list.currentItem ? list.currentItem.height: 0
            border.width: 5

            x: list.currentItem ? list.currentItem.x : 0
            Behavior on x {
                SpringAnimation {
                        spring: 3
                        damping: 0.2
                }
            }

            y: list.currentItem ? list.currentItem.y : 0
            Behavior on y {
                SpringAnimation {
                        spring: 3
                        damping: 0.2
                }
            }
        }*/

        delegate: Rectangle {
            id: rect

            height: 80
            width: parent.width - 2 * border.width

            radius: 15
            border.color: "black"
            border.width: 1
            color: "transparent"

            property real detailsOpacity

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    console.log('clicked')
                    if(rect.state == "Details") {
                        list.currentIndex = -1
                        rect.state = ''
                    } else {
                        list.currentIndex = index
                        rect.state = 'Details'
                    }
                }
            }

            states: State {
                name: "Details"

                PropertyChanges { target: rect; color: "lightsteelblue" }
                PropertyChanges { target: rect; height: widget.height - 5 }
                PropertyChanges { target: rect; detailsOpacity: 1 }
                PropertyChanges { target: list; interactive: false }
                PropertyChanges { target: list; explicit: true; contentY: rect.y }
            }

            transitions: Transition {
                ParallelAnimation {
                    ColorAnimation { property: "color"; duration: 500 }
                    NumberAnimation { duration: 300; properties: "detailsOpacity,x,contentY,height,width" }
                }
            }

            /*Rectangle {
                id: back
                opacity: 0
                anchors.top: parent.top
                anchors.topMargin: 10
                anchors.horizontalCenter: parent.horizontalCenter

                width: label.width + 20; height: label.height + 6
                smooth: true
                radius: 10

                gradient: Gradient {
                    GradientStop { id: gradientStop; position: 0.0; color: palette.light }
                    GradientStop { position: 1.0; color: palette.button }
                }

                SystemPalette { id: palette }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    onClicked: {
                        rect.state = ''
                        list.currentIndex = -1
                    }
                }

                Text {
                    id: label
                    text: 'Назад'
                    anchors.centerIn: parent
                }
            }*/


            Text {
                id: title
                text: tariff.title
                font.pointSize: 20

                anchors.horizontalCenter: parent.horizontalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.top: parent.top
                anchors.topMargin: 10
            }

            Text {
                id: info
                anchors.top: title.bottom
                anchors.left: parent.left
                anchors.leftMargin: 10

                text: tariff.note
                font.pointSize: 16
            }

            Text {
                id: price_info
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.top: parent.top
                anchors.topMargin: 10

                text: price_info.format(tariff)
                font.pointSize: 16

                function format(tariff) {
                    var interval = {1: ' / час', 2: ' / сутки', 3: ' / месяц'}[tariff.interval]
                    if(tariff.type == 3) {
                        interval = ' за раз'
                    }

                    return tariff.costInfo + ' грн.' + interval
                }
            }

            Text {
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.top: price_info.bottom

                text: tariff.zeroTime != '' ? 'Расчетное время: ' + tariff.zeroTime : ''
                font.pointSize: 16
            }

            Text {
                id: explanation
                opacity: detailsOpacity
                text: payment ? payment.explanation : ''
                font.pointSize: 16
                anchors.left: parent.left
                anchors.leftMargin: 25
                anchors.bottom: price.top
                anchors.bottomMargin: 1
            }

            Text {
                id: price
                opacity: detailsOpacity
                text: payment && payment.enabled ? 'К оплате: ' + payment.price + ' грн.': ''
                font.pointSize: 20
                anchors.right: parent.right
                anchors.rightMargin: 25
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 20
            }
        }
    }
}
