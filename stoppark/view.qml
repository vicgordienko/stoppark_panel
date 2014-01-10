import QtQuick 1.1

Rectangle {
    id: widget

    width: 700
    height: 300

    property string message

    function set_message(new_message) {
        message = new_message
    }

    property variant payable
    signal new_payment (variant payment)

    function set_payable(new_payable) {
        payable = new_payable
        for(var i=0; i<model.count; i++) {
            var item = model.get(i)
            model.setProperty(i, 'payment', payable ? payable.pay(item.tariff) : null)
        }
        emit_current_payment()
    }

    function set_tariffs(tariffs) {
        var index = list.currentIndex
        if(index != -1) {
            list.currentItem.state = ''
        }

        model.clear()
        if(tariffs) {
            for(var i=0; i<tariffs.length;i++) {
                var tariff = tariffs[i]
                model.append({
                    tariff: tariff,
                    payment: payable ? payable.pay(tariff) : null
                })
            }

            if(index == -1) {
                index = 0
            }

            if(index < model.count) {
                list.currentIndex = index
                list.currentItem.state = 'Details'
            }
        }
    }

    function emit_current_payment() {
        if(list.currentIndex != -1) {
            var item = model.get(list.currentIndex)
            if(item.payment) {
                new_payment(item.payment)
            } else {
                new_payment(null)
            }
        } else {
            new_payment(null)
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter

        opacity: list.model.count ? 0 : 1

        //text: "Поднесите карточку оператора"
        text: message
        font.pointSize: 25
    }

    ListView {
        id: list
        anchors.top: parent.top
        width: parent.width - 1
        height: parent.height - 1

        spacing: 5
        clip: true
        focus: true
        orientation: ListView.Vertical

        model: ListModel {
              id: model
        }

        onCurrentIndexChanged: {
            //console.log('onCurrentIndexChanged', currentIndex)
            emit_current_payment()
        }

        highlightMoveDuration: 500

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
                    if(rect.state == 'Details') {
                        list.currentIndex = -1
                        rect.state = ''
                    } else {
                        list.currentIndex = index
                        rect.state = 'Details'
                    }
                }
            }

            states: [
                State {
                    name: "Details"

                    PropertyChanges { target: rect; color: "lightsteelblue" }
                    PropertyChanges { target: rect; height: list.height - border.width }
                    PropertyChanges { target: rect; detailsOpacity: 1 }
                    PropertyChanges { target: list; interactive: false }
                    PropertyChanges { target: list; explicit: true; contentY: rect.y }
                }
            ]

            transitions: Transition {
                ParallelAnimation {
                    ColorAnimation { property: "color"; duration: 500 }
                    NumberAnimation { duration: 300; properties: "detailsOpacity,x,contentY,height,width" }
                }
            }

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
                id: priceInfo
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.top: parent.top
                anchors.topMargin: 10

                text: tariff.cost_info
                font.pointSize: 12
            }

            Text {
                id: zeroTime
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.top: priceInfo.bottom

                text: tariff.zero_time_info
                font.pointSize: 12
            }

            Text {
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.top: zeroTime.bottom

                text: tariff.max_per_day_info
                font.pointSize: 12
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
                text: payment && payment.enabled ? payment.price_info : ''
                font.pointSize: 20
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
            }
        }
    }
}
