# ha-oilfox
HomeAssistant Sensor for OilFox using the official customer API.

In my Setup (Home Assistant 2022.9.4) this component is working but it should ne used with caution as his is my first homeassistant component and pyhton project at all. 

If you habe some problems or ideas just let me know!

## Setup
It is listed in HACS, just search for "OilFox".
If you prefer the manual installation, it is done like other custom components :)

## Configuration
If you are not configuration via config flow you can add a new sensor *oilfox* with email and password that your oilfox is connected with 
```yaml
sensor: 
  - platform: oilfox
    email: "<your email>"
    password: "<your password>"
```

**Important:** the yaml configuration will be removed in future releases! Please use the config flow. Configuration within the yaml file will be migrated to the config flow. A warning will be shown if the yaml configuration is migrated to the config flow
```
2022-09-17 17:12:31.584 WARNING (MainThread) [custom_components.oilfox.sensor] Import yaml configration settings into config flow
```
## Result
After installing the component and configure the sensor new entities will be added. Something like *sensor.oilfox_hadwareid_sensor*

Multiple Devices on the OilFox account are supported.

  ![image](https://user-images.githubusercontent.com/10805806/164910584-723ca9ff-d8d0-43ef-b14a-e5239d1ca411.png)

  ![image](https://user-images.githubusercontent.com/10805806/187221763-b7844b6c-1c80-4bb1-b493-f006afa0e0fb.png)

## Logging
For debug log messages you need to adjust the log config for custom_components.oilfox.sensor based on the [HA documentation](https://www.home-assistant.io/integrations/logger/)
Example configuration.yaml
```
logger:
  default: info
  logs:
    custom_components.oilfox.sensor: debug
```

## Battery Entity
The [API](https://github.com/foxinsights/customer-api/tree/main/docs/v1) only provides text based battery status. In order to convert them into some numeric values I used the following mapping:
```
FULL = 100%
GOOD = 70%
MEDIUM = 50%
WARNING" = 20%
CRITICAL = 0%
```

These values should work with [Low battery level detection & notification for all battery sensors](https://community.home-assistant.io/t/low-battery-level-detection-notification-for-all-battery-sensors/258664).

## validationError Entity
The [API](https://github.com/foxinsights/customer-api/tree/main/docs/v1) provides text based validationError status. Used the mappings based on the Documentation:
```
NO_METERING =	No measurement yet
EMPTY_METERING = Incorrect Measurement
NO_EXTRACTED_VALUE = No fill level detected
SENSOR_CONFIG = Faulty measurement
MISSING_STORAGE_CONFIG = Storage configuration missing
INVALID_STORAGE_CONFIG = Incorrect storage configuration
DISTANCE_TOO_SHORT = Measured distance too small
ABOVE_STORAGE_MAX = Storage full
BELOW_STORAGE_MIN = Calculated filling level implausible
```


## Background
This component is using the official [OilFox customer Api](https://github.com/foxinsights/customer-api)

As this is my first homeassistant component there is a lot to impove. If I have time I will try to get this component more to the [homeassisant recommendations](https://developers.home-assistant.io/docs/creating_component_code_review/)
