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
After installing the component and configure the sensor new entities will be added. Something like *sensor.oilfox_hadwareid_sensor*

Multiple Devices on the OilFox account are supported.

  ![image](https://user-images.githubusercontent.com/10805806/164910584-723ca9ff-d8d0-43ef-b14a-e5239d1ca411.png)

  ![image](https://user-images.githubusercontent.com/10805806/164910553-02410e6b-7271-4b3f-bf0e-56485a0d3d8f.png)



## Background
This component is using the official [OilFox customer Api](https://github.com/foxinsights/customer-api)

As this is my first homeassistant component there is a lot to impove. If I have time I will try to get this component more to the [homeassisant recommendations](https://developers.home-assistant.io/docs/creating_component_code_review/)
