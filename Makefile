.PHONY: default
default:
	xcrun xcresulttool formatDescription get --format json | python3 xcresulttool_openapi_generator.py -
