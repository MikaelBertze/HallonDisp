from consolemenu import *
from consolemenu.items import *
from hallondisp.utils.iot_simulators import *

broker = "bulbasaur.bertze.se"


powerSimulator = PowerSensorSimulator(broker, .1, 5, 200)
#powerSimulator.connect()
powerSimulator.run()

tempSimulator = TempSimulator(broker, -10, 30, 200, 5)
#tempSimulator.connect()
tempSimulator.run()

doorSimulator = DoorSimulator(broker, "door1")
#doorSimulator.connect()
doorSimulator.run()



def main():
    menu = ConsoleMenu("Title", "Subtitle")
    for sim in  [powerSimulator, tempSimulator, doorSimulator]:
        function_item = FunctionItem(f"Toggle pause for {sim.name}", sim.toggle_pause)
        menu.append_item(function_item)

    doorState = "Open" if doorSimulator.door_state else "Close"
    menu.append_item(FunctionItem(f"{doorState} door", doorSimulator.toggle_door))

    menu.show()

while True:
    input()
    main()


