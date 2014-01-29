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

    function set_tariffs_with_payable(tariffs, new_payable) {
        if(tariffs === undefined) {
            model.clear()
            return
        }
        payable = new_payable
        list.currentIndex = -1
        var suggested_tariff_idx = -1;
        for(var i=0;i<tariffs.length;i++) {
            var tariff = tariffs[i]
            var payment = payable ? payable.pay(tariff) : null
            if(i < model.count) {
                model.setProperty(i, 'tariff', tariff)
                model.setProperty(i, 'payment', payment)
            } else {
                model.append({
                    tariff: tariff,
                    payment: payment
                })
            }
            if(payment && payment.enabled && payable.tariff === tariff.id) {
                suggested_tariff_idx = i;
            }
        }
        for(var i=tariffs.length;i<model.count;i++) {
            model.remove(i)
        }
        console.log(suggested_tariff_idx)

        if(suggested_tariff_idx != -1 && suggested_tariff_idx != list.currentIndex) {
            /*if(list.currentIndex != -1) {
                    list.currentItem.state = ''
            }*/
            list.currentIndex = suggested_tariff_idx
            //list.currentItem.state = 'Details'
        } else {
            if(payable.tariff !== undefined) {
                list.currentIndex = 0
            }
            emit_current_payment()
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

        text: message
        font.pointSize: 25
    }

    ListView {
        id: list
        anchors.top: parent.top
        width: parent.width - 1
        height: parent.height - 1

        spacing: 3
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

        highlightRangeMode: ListView.StrictlyEnforceRange
        /*highlightFollowsCurrentItem: true
        highlight: Rectangle {
            focus: true
        }
        highlightMoveDuration: 300*/

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
                    /*if(list.currentIndex != -1 && list.currentIndex != index) {
                        list.currentItem.state = ''
                    }*/

                    if(rect.state == 'Details') {
                        list.currentIndex = -1
                        //list.interactive = true
                        //rect.state = ''
                    } else {
                        list.currentIndex = index
                        //list.interactive = false
                        //rect.state = 'Details'
                    }
                }
            }

            states: [
                State {
                    name: "Details"
                    when: index == list.currentIndex
                    PropertyChanges { target: rect; color: "lightsteelblue" }
                    PropertyChanges { target: rect; height: list.height }
                    PropertyChanges { target: rect; detailsOpacity: 1 }
                    StateChangeScript {
                        name: "myScript"
                        script: console.log(index,'->', 'details')
                    }
                }
            ]

            transitions: Transition {
                ParallelAnimation {
                    ColorAnimation { property: "color"; duration: 300 }
                    NumberAnimation { duration: 300; properties: "detailsOpacity,x,height,width" }
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
