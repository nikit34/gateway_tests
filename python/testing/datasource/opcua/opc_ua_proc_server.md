## OPC UA two-processing server

### Example of use in code

```console
from datasource.opcua.opc_ua_proc_server import OpcUaServer

opc = OpcUaServer(
    name_source_dir=common.fixtures_path(__file__) + "/",
    data_points_obj=common.get_fixture("data_points.json"),
    opc_settings_obj=common.get_fixture("opc_ua_settings.json"),
    gen_infinity=True,
    logging_mode="INFO"
)
```

### Class options

* Use parameter `name_source_dir` 
* Use parameter `data_points_obj` 
* Use required parameter `opc_settings_obj` to specify a settings object 
* Use parameter `gen_infinity` to determine the infinity generation mode (default - False)
  Use parameter `gen_infinity` to determine the logging by mode 
  False, "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" (default - False)
  Folder outside the repository with log files will be created, divided by types of variables
