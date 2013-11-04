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
            if(!item.payment) {
                new_payment(item.payment)
            }
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

    Rectangle {
        anchors.top: list.bottom
        anchors.horizontalCenter: parent.horizontalCenter

        height: parent.height - list.height
        width: parent.width

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter

            text: 'Тариф: ' + model.get(list.currentIndex).tariff.title
            font.pointSize: 25
        }

        Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter

            text: list.currentIndex != -1 ? 'Сумма к оплате: ' + model.get(list.currentIndex).payment.price : ''
            font.pointSize: 25
        }
    }

    ListView {
        id: list
        anchors.top: parent.top
        width: parent.width

        height: 245

        focus: true
        orientation: ListView.Horizontal

        model: ListModel {
              id: model
        }

        onCurrentIndexChanged: {
            emit_current_payment()
        }

        highlightMoveDuration: 500
        highlightFollowsCurrentItem: false
        highlight: Rectangle {
            color: "lightgreen"
            radius: list.currentItem ? list.currentItem.radius: 0
            width: list.currentItem ? list.currentItem.width: 0
            height: list.currentItem ? list.currentItem.height: 0
            border.width: 10

            x: list.currentItem ? list.currentItem.x : 0
            Behavior on x {
                SpringAnimation {
                        spring: 3
                        damping: 0.2
                }
            }
        }

        delegate: Rectangle {
            id: rect

            height: parent.height
            width: widget.width

            color: "transparent"

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    list.currentIndex = index
                }
            }

            radius: 15
            border.color: "black"
            border.width: 1

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

                text: tariff.zeroTime ? 'Расчетное время: ' + tariff.zeroTime : ''
                font.pointSize: 16
            }

            Text {
                text: payment ? payment.explanation : ''
                font.pointSize: 16
                anchors.left: parent.left
                anchors.leftMargin: 25
                anchors.bottom: price.top
                anchors.bottomMargin: 1
            }

            Text {
                id: price
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
