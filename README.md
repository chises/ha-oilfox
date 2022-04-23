# ha-oilfox
HomeAssistant Sensor for OilFox using the official customer API.

In my Setup (Home Assistant 2022.4.6 with core-2022.4.6) this component is working but it should ne used with caution as his is my first homeassistant component and pyhton project at all. 

If you habe some problems or ideas just let me know!

## Setup
nothing special, install like all others custom components :)

## Configuration
Add a new sensor *oilfox* with email and password that your oilfox is connected with 
```yaml
sensor: 
  - platform: oilfox
    email: "<your email>"
    password: "<your password>"
```
## Result
After installing the component and configure the sensor new entities will be added. Something like *sensor.oilfox_<hadwareid>_<sensor>
Multiple Devices on the OilFox account are supported.

![image](https://user-images.githubusercontent.com/10805806/164026064-9a6412e5-19fe-46d3-b9d7-ea4f1627ec21.png)


## background
This component is using the official [OilFox customer Api](https://github.com/foxinsights/customer-api)

As this is my first homeassistant component there is a lot to impove. If I have time I will try to get this component more to the [homeassisant recommendations](https://developers.home-assistant.io/docs/creating_component_code_review/)
