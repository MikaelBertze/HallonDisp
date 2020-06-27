# HallonDisp
Module based framework for small display applications.

## The UI
The UI is built up by 'pages' that contains 'widgets'. A widget could contain anything as long as it derive from a Tk Frame.
The main UI display a page (with widgets) and 2 buttons for navigating between the pages.

Pages can contain any number of widgets as long as they fit the screen size. The framework is built to support small touch-screens why there is no scroll bars displayed if the page overflow the screen size.

![HallonDisp screenshot](/images/HallonWidget.png?raw=true)

*Arrows on left and right side swith the active 'page'. The displayed page contain 4 widgets. LocalTimeWidget, CurrentPowerWidget, TemperatureWidget and DoorWidget.*

# The backround workers
You often need some kind of backround worker that either listen to or fetch data from some device. For this you can use a HallonWorker that runs on its own thread. A HallonWorker can then publich updates to the UI whenever new data is available.

There are some built-in workers that handle a few different IoT devices. Most of them subscribe on mqtt messages, process the message and then publich a ui friendly message through a Rx subject. The connextion between a widget and its requiered workers are defined in the configuration file `hallondisp.json`.

A HallonWorker can be shared between multiple HallonWidgets. This makes it possible to have multiple widges backed by the same data source 

### Example
#### PowerWidgets
- IoT

  A blink-detector that send a mqtt message whenever the power-meter blinks. The IoT publich all messages on the topic `power` as a json string containg the time since last blink and an IoT id.
  
  
  ```
  { 
    "id" : "10702547_3",
    "power_tick_period" : 908
  }
  ```
- PowerWorker
  The worker subscribe on the topic `power`. When a message is recieved it extracts the `power_tick_period` and calculates the current power. The power is the publiched on the Rx subject `whenPowerReported`.
- CurrentPowerWidget
  The widget require a worker of type `PowerWorker`. At construction, the widget subscribes on `whenPowerReported` and updates the power-label when a new current power is reported.

