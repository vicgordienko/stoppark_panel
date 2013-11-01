import QtQuick 1.1

ListView {
    id: widget

    width: 700
    height: 300

    focus: true
    orientation: ListView.Horizontal

    function set_tariffs(tariffs) {
        var index = currentIndex
        model.clear()
        for(var i=0; i<tariffs.length;i++) {
            var tariff = tariffs[i]
            model.append({
                tariff: tariff,
                payment: ticket ? ticket.pay(tariff) : null
            })
        }
        currentIndex = index
    }

    model: ListModel {
        id: model
    }

    property variant ticket

    /*onTicketChanged: {
        console.log('ticketChanged', ticket)
        for(var i=0; i<model.count; i++) {
            var item = model.get(i)
            model.setProperty(i, 'payment', ticket ? ticket.pay(item.tariff) : null)
        }
    }*/

    signal new_payment (variant payment)

    onCurrentIndexChanged: {
        console.log('index_changed')
        if(currentIndex != -1) {
            var item = model.get(currentIndex)
            if(item.payment && item.payment.enabled) {
                new_payment(item.payment)
            }
        }
    }

    highlightMoveDuration: 500
    highlightFollowsCurrentItem: true
    highlight: Rectangle {
        color: "lightsteelblue"
        radius: widget.currentItem.radius
    }

    delegate: Rectangle {
        id: rect

        height: parent.height
        width: 500
        radius: 25

        color: "transparent"

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
            text: tariff.title
            font.pointSize: 22

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 10
        }

        Text {
            id: info
            text: info.format(tariff)
            font.pointSize: 18

            function format(tariff) {
                var interval = {1: ' / час', 2: ' / сутки', 3: ' / месяц'}[tariff.interval]
                if(tariff.type == 3) {
                    interval = ' за раз'
                }

                return tariff.note + '\n' + tariff.costInfo + ' грн.' + interval
            }

            anchors.top: text.bottom
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: payment ? payment.explanation : ''
            font.pointSize: 16
            anchors.left: parent.left
            anchors.leftMargin: 25
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 25
        }
    }
}
