# OPC UA server

## Prerequisites

You should prepare your environment according to project `README.md`.

Generate key and certificate:

```shell
openssl genpkey -out server.key -outform DER -algorithm RSA -pkeyopt rsa_keygen_bits:2048
openssl req -nodes -x509 -sha256 -days 365 -key server.key -keyform DER \
  -subj "/C=RU/ST=Moscow/L=Moscow/O=Adaptive Production Technology, LLC/OU=IT/CN=IKS 1000GP OPC UA Server (Example)" \
  -out server.crt -outform DER \
  -addext "subjectAltName = DNS:localhost, IP:127.0.0.1, URI:urn:APROTECH:IKS1000GP:OpcUaServer"
```
## Launching

In order to launch OPC UA server in pipenv environment:

```shell
./opc_ua_server.py
```

## Description

The server generates new values with the interval set in the field `sleepInterval` in 
the `opc_ua_settings.json` and `data_points.json` files for the following variables:  
  * `Boolean` - Boolean variable
  * `Int` - Integer variable
  * `Long` - Long variable
  * `Double` - Double variable
  * `String` - String variable (length 255)

You can find corresponding MindSphere asset `TGW_TestAsset` on APROTECH tenant.
