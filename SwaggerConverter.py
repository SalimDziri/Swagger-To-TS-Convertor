import yaml
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate an api.ts file from a YAML file')

    # Add an argument to specify the YAML config file
    parser.add_argument('-C', '--config', type=str, help='YAML config file path', required=True)

    # Parse command-line arguments
    args = parser.parse_args()

    # Read the YAML file
    with open(args.config, 'r') as config_file:
        config_data = yaml.safe_load(config_file)

    # Check if the required keys are present in the YAML file
    required_keys = ['file', 'output', 'server', 'project']
    for key in required_keys:
        if key not in config_data:
            parser.error(f"Missing '{key}' key in the YAML config file.")

    return argparse.Namespace(**config_data)

# Parse command-line arguments
args = parse_arguments()

def convert_type(data_type):
    type_mapping = {
        'integer': 'bigint',
        'string': 'string',
        'boolean': 'boolean',
        'array': 'any[]',
        'object': 'any',
        'number': 'number'
    }
    return type_mapping.get(data_type, 'any')

def generate_endpoint_with_parameters(path, parameters):
    for parameter in parameters:
        parameter_name = parameter['name']
        parameter_in = parameter['in']
        if parameter_in == 'query':
            continue
        path = path.replace(f"{{{parameter_name}}}", f"${{{parameter_name}}}")
    return path

def generate_query_parameters(query_parameters):
    query_params = []
    for parameter in query_parameters:
        parameter_name = parameter['name']
        parameter_type = convert_type(parameter['schema']['type'])
        query_params.append(f"{parameter_name}?: {parameter_type}")
    return ', '.join(query_params)

def generate_endpoint_with_query(path, query_parameters):
    query_params = []
    for parameter in query_parameters:
        parameter_name = parameter['name']
        parameter_value = f"${{{parameter_name}}}"
        query_params.append(f"{parameter_name}={parameter_value}")
    query_string = '&'.join(query_params)
    if query_string:
        return f"{path}?{query_string}"
    return path

def generate_path_parameters(parameters):
    path_params = []
    for parameter in parameters:
        parameter_name = parameter['name']
        parameter_in = parameter['in']
        if parameter_in == 'path':
            parameter_type = convert_type(parameter['schema']['type'])
            path_params.append(f"{parameter_name}: {parameter_type}")
    if path_params == []:
        return ''
    return ', '.join(path_params)+', '

def get_response_description(response_details):
    content = response_details.get('content', {})
    if content:
        for media_type, media_details in content.items():
            schema = media_details.get('schema', {})
            if '$ref' in schema:
                return schema['$ref'].split('/')[-1]
            elif 'items' in schema and '$ref' in schema['items']:
                return schema['items']['$ref'].split('/')[-1]+"[]"
    return response_details.get('description', '')

# hundle optional query usage
def generate_query_string(query_parameters):
    query_string = ""
    for parameter in query_parameters:
        parameter_name = parameter['name']
        query_string += f"  if ({parameter_name} !== undefined) {{\n"
        query_string += f"    query += (query === '' ? '?' : '&') + '{parameter_name}=' + encodeURIComponent({parameter_name}.toString());\n"
        query_string += "  }\n"
    return query_string

## go throw the yml file and generate ts code based on the result
def convert_to_ts_format(spec_file, output_file):
    with open(spec_file, 'r') as f:
        spec = yaml.safe_load(f)

    
    version = spec['info']['version']

    ts_code = "/*\n"
    ts_code += f" * API Endpoints Documentation for {args.project} Web Client \n"
    ts_code += " *\n"
    ts_code += f" * This TypeScript file provides a collection of {args.project} API endpoints. \n"
    ts_code += " * It includes the definitions for request/response structures, and various operations supported by the API. \n"
    ts_code += " *\n"
    ts_code += f" * OpenAPI spec version: {version}\n"
    ts_code += " * \n"
    ts_code += " * \n"
    ts_code += " * This code was auto generated with SwaggerConverter.py \n"
    ts_code += " * \n"
    ts_code += " * Do Not edit this code manually \n"
    ts_code += " * \n"
    ts_code += " * Use SwaggerConverter to update this file if necessary \n"
    ts_code += " */ \n\n"

    # export the endpoint interface
    ts_code += "export interface Endpoint { \n"
    ts_code += "    path: string \n"
    ts_code += "    method: string \n"
    ts_code += "} \n\n\n"

    # Use a globel varibale for server
    ts_code += "/** WebServer baseUrl */ \n"
    ts_code += f"export const baseUrl = \"{args.server}\"\n\n"
    
    # Check (paths) section in the yaml file
    for path, methods in spec['paths'].items():
        for method, details in methods.items():
            # get the path summary and description if it exists
            summary = details.get('summary', 'No summary available')
            description = details.get('description', '')

            ts_code += "/**\n"
            ts_code += f" * {summary}\n"
            ts_code += "\n"
            ts_code += f" * {description}\n"
            ts_code += " *\n"
            ts_code += f" * type: {method.upper()}\n"

            # search for request body if it exists
            request_body = details.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                for media_type, media_details in content.items():
                    schema = media_details.get('schema', {})
                    example = media_details.get('example', {})
                    if '$ref' in schema:
                        interface_name = schema['$ref'].split('/')[-1]
                        ts_code += f"\n * request body ({media_type}) :\n"
                        ts_code += f" * - {interface_name} (required)"
                        if 'description' in media_details:
                            ts_code += f" : {media_details['description']}"
                        ts_code += "\n"
                        if example:
                            ts_code += f" * - example: {example}\n"
            # Add path parameters if present
            parameters = details.get('parameters', [])
            path_parameters = [p for p in parameters if p['in'] == 'path']
            if path_parameters:
                ts_code += "\n * path parameters:\n"
                for parameter in path_parameters:
                    parameter_name = parameter['name']
                    parameter_description = parameter.get('description', '')
                    ts_code += f" * - {parameter_name}: {parameter_description} (required)\n"

            # Add query parameters if present
            query_parameters = [p for p in parameters if p['in'] == 'query']
            if query_parameters:
                ts_code += "\n * query parameters:\n"
                for parameter in query_parameters:
                    parameter_name = parameter['name']
                    parameter_description = parameter.get('description', '')
                    ts_code += f" * - {parameter_name}: {parameter_description}\n"


            ts_code += "\n"
            # search for responses
            ts_code += " * responses:\n"
            responses = details.get('responses', {})
            for response_code, response_details in responses.items():
                response_description = get_response_description(response_details)
                ts_code += f" * - {response_code}: {response_description}\n"

            ts_code += " */\n"
            operation_id = details.get('operationId', '')
            parameters = details.get('parameters', [])
            query_parameters = [p for p in parameters if p['in'] == 'query']
            path_with_parameters = generate_endpoint_with_parameters(path, parameters)
            path_with_query = generate_endpoint_with_query(path_with_parameters, query_parameters)

            #if parameters:
            #    if query_parameters:
            #        ts_code += f"export const {operation_id}Endpoint = ({generate_query_parameters(query_parameters)}, {generate_path_parameters(parameters)}) => `{path_with_query}`\n"
            #    else:
            #        ts_code += f"export const {operation_id}Endpoint = ({generate_path_parameters(parameters)}) => `{path_with_parameters}`\n"
            #else:
            #    ts_code += f"export const {operation_id}Endpoint = () => `{path}`\n"
            #ts_code += "\n"
            if parameters:
                if query_parameters:
                    ts_code += f"export const {operation_id}Endpoint = ({generate_path_parameters(parameters)} {generate_query_parameters(query_parameters)}) => {{\n"
                    #ts_code += f"  return {{ path: `{path_with_query}`, method: '{method.upper()}' }};\n"
                    ts_code += f"  let query = '';\n"
                    ts_code += generate_query_string(query_parameters)
                    ts_code += f"  return {{ path: `{path_with_parameters}${{query}}`, method: '{method.upper()}' }};\n"
                    ts_code += "}\n"
                else:
                    ts_code += f"export const {operation_id}Endpoint = ({generate_path_parameters(parameters)}) => {{\n"
                    ts_code += f"  return {{ path: `{path_with_parameters}`, method: '{method.upper()}' }};\n"
                    ts_code += "}\n"
            else:
                ts_code += f"export const {operation_id}Endpoint = () => {{\n"
                ts_code += f"  return {{ path: `${{baseUrl}}{path}`, method: '{method.upper()}' }};\n"
                ts_code += "}\n"
            ts_code += "\n"

    with open(output_file, 'w') as f:
        f.write(ts_code)

    print(f"TypeScript file generated: {output_file}")

convert_to_ts_format(args.file, args.output)
