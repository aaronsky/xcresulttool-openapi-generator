#!/usr/bin/env python3

import argparse
import json
import sys
from typing import Any, IO, Dict, List, Literal, Tuple, TypedDict, Union


OpenAPIInfo = TypedDict('OpenAPIInfo', {
    'title': str,
    'version': str,
    'x-signature': str,
})

class JSONSchemaPropertyAny(TypedDict):
    pass
class JSONSchemaPropertyTyped(TypedDict):
    type: str
class JSONSchemaPropertyTypedFormatted(TypedDict):
    type: str
    format: str
class JSONSchemaPropertyTypedArray(TypedDict):
    type: Literal['array']
    items: 'JSONSchemaProperty'

JSONSchemaReference = TypedDict('JSONSchemaReference', {'$ref': str})

JSONSchemaProperty = Union[
    JSONSchemaReference,
    JSONSchemaPropertyTypedArray,
    JSONSchemaPropertyTypedFormatted,
    JSONSchemaPropertyTyped,
    JSONSchemaPropertyAny,
]

JSONSchemaProperties = Dict[str, JSONSchemaProperty]

class JSONSchemaType(TypedDict):
    type: str
    properties: JSONSchemaProperties
    additionalProperties: Literal[False]
    required: List[str]

class JSONSchemaComposing(TypedDict):
    allOf: List[Union[JSONSchemaReference, JSONSchemaType]]

JSONSchema = Union[JSONSchemaComposing, JSONSchemaReference, JSONSchemaType]

class OpenAPIComponents(TypedDict):
    schemas: Dict[str, JSONSchema]

class OpenAPISpec(TypedDict):
    openapi: str
    info: OpenAPIInfo
    components: OpenAPIComponents


def openAPISpec(
    openapi_version: str,
    title: str,
    version: tuple[int, ...],
    signature: str,
    schemas: Dict[str, JSONSchema]
) -> OpenAPISpec:
    return {
        'openapi': openapi_version,
        'info': {
            'title': title,
            'version': f'{version[0]}.{version[1]}',
            'x-signature': signature,
        },
        'components': {
            'schemas': schemas
        }
    }


def dataType(t: str) -> JSONSchemaProperty:
    match t:
        case 'Bool':
            return {'type': 'boolean'}
        case 'Int':
            return {'type': 'integer'}
        case 'Double':
            return {'type': 'number', 'format': 'double'}
        case 'String':
            return {'type': 'string'}
        case 'Date':
            return {'type': 'string', 'format': 'date-time'}
        case 'SchemaSerializable':
            return {}
        case _:
            return {'$ref': f'#/components/schemas/{t}'}


def schemaType(t: Dict[str, Any]) -> Tuple[str, List[Union[JSONSchemaReference, JSONSchemaType]]]:
    title = t['type']['name']
    kind = t['kind']
    if kind == 'value' or kind == 'array':
        return (title, [])
    assert kind == 'object'

    schemas: List[Union[JSONSchemaReference, JSONSchemaType]] = []

    supertype = t['type'].get('supertype')
    if supertype:
        schemas.append({'$ref': f'#/components/schemas/{supertype}'})

    properties: JSONSchemaProperties = {}
    required_properties = []
    for prop in t['properties']:
        prop_name = prop['name']
        prop_type = prop['type']
        prop_wrapped_type = prop.get('wrappedType')
        prop_is_optional = prop['isOptional']

        if prop_type == 'Array':
            assert prop_wrapped_type
            properties[prop_name] = {
                'type': 'array',
                'items': dataType(prop_wrapped_type),
            }
        elif prop_type == 'Optional':
            assert prop_is_optional and prop_wrapped_type
            properties[prop_name] = dataType(prop_wrapped_type)
            required_properties.append(prop_name)
        else:
            properties[prop_name] = dataType(prop_type)
    schemas.append({
        'type': kind,
        'properties': properties,
        'additionalProperties': False,
        'required': required_properties,
    })
    return (title, schemas)


def gen_openapi(input: IO[str], openapi_version: str) -> OpenAPISpec:
    xcrt_desc = json.load(input)
    all_schemas: Dict[str, JSONSchema] = {}
    for xcrt_type in xcrt_desc['types']:
        title, schemas = schemaType(xcrt_type)
        if len(schemas) == 0:
            continue
        elif len(schemas) == 1:
            all_schemas[title] = schemas[0]
        else:
            all_schemas[title] = {'allOf': schemas}
    return openAPISpec(
        openapi_version=openapi_version,
        title=xcrt_desc['name'],
        version=(
            xcrt_desc['version']['major'],
            xcrt_desc['version']['minor'],
        ),
        signature=xcrt_desc['signature'],
        schemas=all_schemas,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        usage='Generates xcresulttool format_description as openapi spec'
    )
    parser.add_argument(
        'infile',
        nargs='?',
        type=argparse.FileType('r'),
        default=sys.stdin
    )
    parser.add_argument(
        'outfile',
        nargs='?',
        type=argparse.FileType('w'),
        default=sys.stdout
    )
    args = parser.parse_args()
    json.dump(
        gen_openapi(
            args.infile,
            '3.1.0',
        ),
        args.outfile,
    )


if __name__ == '__main__':
    main()
