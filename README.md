# xcresulttool-openapi-generator

A script to convert the xcresulttool format description into an OpenAPI spec

## Usage

```shell
xcrun xcresulttool formatDescription get --format json | python3 xcresulttool_openapi_generator.py - > xcresulttool_openapi_spec.json
```
