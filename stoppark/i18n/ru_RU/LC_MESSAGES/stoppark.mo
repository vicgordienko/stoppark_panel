��    w      �  �   �      
  �   
     �
     �
  N   �
     G     J  *   M    x     �     �     �     �     �  '   �     �  3        8     K     a     j  �   y     �  "        )  
   H     S  (   _  3   �     �  �   �     z  �   �       	     #         D     R     a     p  0   ~     �     �  a   �     %     -     ;     P     d     u     �     �     �     �     �     �     �     �     �  =   �     6     R     [  
   z     �     �     �     �     �  7   �               !     :  	   I     S     b     r     �  	   �     �     �     �     �     �     �     �  (        >     D     Q     X  
   v     �     �     �     �     �     �  +   �     �  
   �  
   	          !  �   (     �     �     �               !     &     .  
   3  
   >     I     V     e  B  r  �   �     �     �  c   �            C   !  �  e  $   �          4  
   S     ^  :   y     �  c   �     /     N     m     �  �   �     x  E   �  1   �      �        :   ?  E   z      �  �   �  ;   �   �    !     �!     �!  `   �!     ?"  ,   _"     �"  +   �"  ]   �"     .#     G#  �   f#  
   �#     �#  $   $  3   =$  *   q$     �$  #   �$     �$  .   �$  #   %     )%     @%     E%     V%     g%  Y   t%  .   �%     �%  r   
&     }&  .   �&  4   �&     �&  "   '     8'  B   P'     �'     �'  8   �'     (     (     /(  '   J(  !   r(  -   �(     �(  +   �(     )  #   )  
   =)  "   H)  $   k)  <   �)  Q   �)     *  '   8*     `*  +   q*     �*     �*  6   �*     �*     �*     +     9+  A   T+     �+     �+     �+  $   �+     ,  �   ,      -  $   -  *   4-  &   _-  (   �-     �-     �-     �-     �-     �-     .     .     2.            .           ?      1   -           j   a   
              %   e   N                  6                  s   K   A       +   8   I   M   7   R       0       '       /   U      E   O          3   ;   Q   4   F      c   G      !   g      ,      H   <   W   C       l   D              P       `   &         :   t           o   r   [   Z   ]   =          i   B   $   \   X      u           f   #   _       k                     Y       9   q   d                 m   *       5   L   J       p          v       ^       @           )           T   w   "          n            h      >         V   S   b   (   2       	      entry time: %(time_in)s
payment time: %(now)s
      tariff: %(cost_info)s
parking duration: %(duration)s
  paid until: %(paid_until)s
<hr />
Price: $%(price)s
<hr />
<<%(bar)s>> $%(cost)s/%(interval)s %(begin)s - %(end)s %(fio)s.
[%(make)s] [%(number)s] [%(status)s]
Valid from %(begin)s to %(end)s
 %X %x <c><b>P A R K I N G  T I C K E T</b></c>

 <c><s>Report on period</s></c>

from {self.begin}
to {now}
all places: {self.total_places}
      free: {self.free_places}
        in: {self.moved_in}
       out: {self.moved_out}
   tickets: {self.ticket_moved_out}
     cards: {self.card_moved_out}

       Sum: {self.sum}

 <c>TEMPORARY REPORT</c> Access denied. Access permitted. Addr Admin After refill: from %(begin)s to %(end)s Antipassback Automatic system
of payed parking
STOP-Park
<hr />
 BAR Access denied. BAR Access permitted. BAR Left Begin session? CARD-SYSTEMS
Kyiv
Peremohy ave, 123
(+380 44) 284 0888
EXAMPLE
CAUTION! Do not crumple tickets!
Ticket loss will be penalized
EXAMPLE Cancel Cannot be refilled by this tariff. Cannot connect to concentrator Car inside Car outside Card #%(id)s
%(fio)s
Access: %(access)s
 Card #%(id)s
%(fio)s
Access: %(access)s

%(report)s Card %(sn)s
%(fio)s
 Card %(sn)s
%(tariff)s: %(cost_info)s
Before refill: from %(begin)s to %(end)s
%(refill)s
After refill: from %(new_begin)s to %(new_end)s
<hr />
Price: %(price)s
<hr /> Card at terminal Cash: ${self.sum}
Moved inside: %{self.moved_in}
Moved outside: %{self.moved_out}
Moved outside using card: %{self.card_moved_out}
 Config Configure Configure and update terminal list: DB server IP: Database Error Date and time: Display test: Duration: %(duration)s.
Payment units: %(units)i Enable End session? Extra payment for ticket: %(bar)s.
Time in: %(time_in)s.
Last payment: %(base_time)s.
%(details)s General Input barcode Manual barcode input Manual ticket print Max per day: $%i Moved inside: %s
<hr />
 Network connection: No No paper at terminal %i No tariffs to display Notification OK Operator Pay Payment Payment for ticket %(bar)s.
Time in: %(time_in)s.
%(details)s Payment has been successful Payments Perform global terminal setup: Price: $%i Print temporary report Query Error Refill for  Report generation... Session begin Session completed by: %s
<c>***SESSION COMPLETED***</c> Session end Setup Setup network connection Single payment Stop-Park Surcharge: $%i Terminal config Terminal list Terminal setup Terminals Terminals error Test display Test message Tests Ticket %s already out. Ticket %s already paid. Ticket %s payment undefined. Ticket %s.
Not payable with this tariff. Title Unknown card Update Update: %(message)s (%(now)s) Update: %s Version: Waiting for operator card... Yes Zero time:  _Refill for  auto date: %(now)s
%(tariff)s: $%(price)s
<hr /> day days day_ days_ hour hours hour_ hours_ inside last payment: %(base_time)s
   surcharge: %(now)s
      tariff: %(cost_info)s
parking duration: %(duration)s
  paid until: %(paid_until)s
<hr />
Price: $%(price)s
<hr />
<<%(bar)s>> manual minute minutes minute_ minutes_ month months month_ months_ open outside pass successful unit units unit_ units_ unknown status unsuccessful Project-Id-Version: Stoppark-1.0
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2014-02-11 14:41+0200
PO-Revision-Date: 2014-02-11 14:55+0200
Last-Translator: Feanor <std.feanor@gmail.com>
Language-Team: stdk <http://github.com/stdk>
Language: ru_RU
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);
X-Poedit-SourceCharset: UTF-8
X-Poedit-Basepath: s:\a13\stoppark\stoppark\
X-Poedit-KeywordsList: _
X-Generator: Poedit 1.5.7
  в'їзд: %(time_in)s
оплата: %(now)s
 тариф: %(cost_info)s
тривалість: %(duration)s
оплачено до: %(paid_until)s
<hr />
Вартість: %(price)s грн.
<hr />
<<%(bar)s>> %(cost)s грн./%(interval)s %(begin)s - %(end)s %(fio)s.
[%(make)s] [%(number)s] [%(status)s]
Действительна с %(begin)s по %(end)s
 %X %x <c><b>П А Р К У В А Л Ь Н И Й  Т А Л О Н</b></c>

 <c><s>Звіт за період</s></c>

з {self.begin}
по {now}
паркомісць разом: {self.total_places}
         вільних: {self.free_places}
          вїздів: {self.moved_in}
         виїздів: {self.moved_out}
         разових: {self.ticket_moved_out}
       постійних: {self.card_moved_out}

     Сума в касі: {self.sum} грн.

 <c>ТИМЧАСОВИЙ ЗВІТ</c> Доступ запрещен. Доступ разрешен. Адрес Администратор После пополнения: с %(begin)s по %(end)s Антипассбек Автоматизована система
платного паркування
STOP-Park
<hr />
 Доступ запрещен. Доступ разрешен. Выезд по талону Начать смену? ТОВ "КАРД-СIСТЕМС
м. Київ
проспект перемоги, 123
(+380 44) 284 0888
ЗРАЗОК
УВАГА! Талон не згинати
ЗА ВТРАТУ ТАЛОНУ ШТРАФ
ЗРАЗОК Отмена Невозможно пополнить по этому тарифу. Нет связи с концентратором Въезд по карточке Выезд по карточке Карточка #%(id)s
%(fio)s
Доступ: %(access)s
 Карточка #%(id)s
%(fio)s
Доступ: %(access)s

%(report)s Карточка %(sn)s
%(fio)s
 Картка %(sn)s
%(tariff)s: %(cost_info)s
До поповнення: з %(begin)s по %(end)s
%(refill)s
Після поповнення: з %(new_begin)s по %(new_end)s
<hr />
Вартість: %(price)s грн.
<hr /> Поднесение карточки к терминалу Сумма в кассе: {self.sum} грн.
Въехало: {self.moved_in}
Выехало всего: {self.moved_out}
Выехало по карточкам: {self.card_moved_out}
 Настройки Настроить Выполнить настройку и обновление списка терминалов: Адрес сервера БД: Нет связи с базой данных Дата и время: Выполнить тест дисплея: Длительность парковки: %(duration)s.
Единиц оплаты: %(units)i Активировать Завершить смену? Доплата по талону %(bar)s.
Время въезда: %(time_in)s
Последняя оплата: %(base_time)s.
%(details)s Общее Введите баркод Ручной ввод баркода Режим ручной печати баркода Максимум за день: %i грн. В'їзд: %s
 Подключение к сети: Нет Нет бумаги на терминале %i Тарифы отсутствуют Уведомление ОК Оператор Оплатить Оплата Оплата по талону %(bar)s.
Время въезда: %(time_in)s.
%(details)s Оплата выполнена успешно Оплата Выполнить установку параметров для всех терминалов в системе: Оплата: %i грн. Печать временного отчёта Ошибка запроса к базе данных Пополнение на  Генерация отчёта... Начало смены Зміну здав: %s
<c>***ЗМІНУ ЗАВЕРШЕНО***</c> Завершение смены Установить Настроить сетевое подключение Разовая оплата Стоп-Парк Доплата: %i грн. Настройка терминалов Список терминалов Конфигурация терминалов Терминалы Нет связи с терминалами Тест дисплея Тестовое сообщение Тесты Талон уже %s выехал. Талон %s уже оплачен. Оплата по талону %s не определена. Талон %s.
Невозможно оплатить по этому тарифу Наименование Неизвестная карточка Обновить Обновление: %(message)s (%(now)s) Обновлено: %s Версия: Поднесите карточку оператора Да Расчетное время:  Поповнення на  автоматически дата друку: %(now)s
%(tariff)s: %(price)s грн.
<hr /> день дня дней доба доби діб час часа часов година години годин внутри остання оплата: %(base_time)s
       доплата: %(now)s
тариф: %(cost_info)s
тривалість: %(duration)s
оплачено до: %(paid_until)s
<hr />
Вартість: %(price)s грн.
<hr />
<<%(bar)s>> вручную минута минуты минут хвилина хвилини хвилин месяц месяца месяцев місяць місяці місяців открытие снаружи проезд успешно раз раза раз раз рази разів неизвестно не удалось 